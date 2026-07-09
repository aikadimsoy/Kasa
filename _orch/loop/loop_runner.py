# -*- coding: utf-8 -*-
"""
KASA loop — otonom test -> duzelt -> yeniden-test motoru (SIFIR-TOKEN, guard'li tam-oto).

Is panosunu (board.json) okur; her is icin:
  1. pytest test_file izole kosar. PASS + regression-watch degilse -> green, atla.
  2. FAIL ise max_iters tur: deepseek taslak -> qwen inceleme -> guard (py_compile+needle)
     -> .bak al + splice -> test_file + regresyon setini tekrar kos.
     PASS + regresyon bozulmadi -> green, tut. Degilse .bak'tan geri al, sonraki tur.
  3. Tur bitince yesil degilse -> orijinali geri yukle, blocked.
Her adim journal + jsonl'e yazilir; opsiyonel `sink` (PlanAgent EventBus koprusu) cagirilir.
Fix kodunu YALNIZ yerel modeller uretir; Claude token harcamaz.
"""
import os, sys, json, time, subprocess, argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_pipe
import guard

DEFAULT_PY = os.environ.get(
    "KASA_PY",
    "C:/Users/REDACTED-USER/AppData/Local/Python/pythoncore-3.14-64/python.exe")


def _now():
    return datetime.now(timezone.utc).isoformat()


class LoopRunner:
    def __init__(self, board_path, py_exe=DEFAULT_PY, sink=None, dry_run=False):
        self.board_path = board_path
        self.py_exe = py_exe
        self.sink = sink              # opsiyonel: callable(record_dict) — PlanAgent koprusu
        self.dry_run = dry_run
        with open(board_path, encoding="utf-8") as f:
            self.board = json.load(f)
        self.repo = self.board["meta"]["repo_root"]
        self.regression_always = self.board["meta"].get("regression_always", [])
        self.out_dir = os.path.join(HERE, "logs")
        os.makedirs(self.out_dir, exist_ok=True)
        self.journal_path = os.path.join(self.out_dir, "loop_journal.md")
        self.events_path = os.path.join(self.out_dir, "loop_events.jsonl")
        self.kpi_path = os.path.join(self.out_dir, "loop_kpi.json")

    # ---- olay yayini -------------------------------------------------------
    def emit(self, kind, **payload):
        rec = {"ts": _now(), "kind": kind, **payload}
        try:
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(f"- `{rec['ts']}` **{kind}** {json.dumps(payload, ensure_ascii=False)}\n")
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except IOError:
            pass
        if self.sink:
            try:
                self.sink(rec)
            except Exception:
                pass
        print(f"[LOOP] {kind}: {json.dumps(payload, ensure_ascii=False)}", flush=True)

    # ---- pytest ------------------------------------------------------------
    def run_pytest(self, test_files):
        """test_files listesini tek pytest kosusunda calistirir. (passed, tail_output)."""
        if isinstance(test_files, str):
            test_files = [test_files]
        cmd = [self.py_exe, "-m", "pytest", "-q", *test_files]
        try:
            proc = subprocess.run(cmd, cwd=self.repo, capture_output=True, text=True, timeout=600)
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, out[-4000:]
        except subprocess.TimeoutExpired:
            return False, "pytest TIMEOUT (>600s)"
        except Exception as e:
            return False, f"pytest calistirma hatasi: {e}"

    def regression_set(self, exclude_test=None):
        """smoke + green/regression-watch islerin testleri (mevcut olanlar)."""
        tests = list(self.regression_always)
        for job in self.board["jobs"]:
            if job.get("status") in ("green", "regression-watch"):
                tf = job.get("test_file")
                if tf and tf != exclude_test:
                    tests.append(tf)
        # yalniz var olan dosyalar + dedup
        seen, out = set(), []
        for t in tests:
            if t in seen:
                continue
            seen.add(t)
            if os.path.exists(os.path.join(self.repo, t)):
                out.append(t)
        return out

    # ---- tarayici saglik kapisi (opsiyonel, job.browser_gate ile tetiklenir) --
    def _run_browser_gate(self, mode):
        """browser_gate.py'yi cagirir; modul yoksa/hata olursa fail-closed (False, {...})."""
        try:
            import importlib
            if "browser_gate" in sys.modules:
                importlib.reload(sys.modules["browser_gate"])
            else:
                import browser_gate  # noqa: F401
            return sys.modules["browser_gate"].run_gate(mode=mode, timeout_s=16)
        except Exception as e:
            return False, {"error": f"browser_gate yuklenemedi: {e}"}

    # ---- tek is ------------------------------------------------------------
    def run_job(self, job):
        jid = job["id"]
        target = os.path.join(self.repo, job["target_file"])
        test_file = job.get("test_file")
        self.emit("job_start", id=jid, title=job.get("title"), status=job.get("status"),
                  dry_run=self.dry_run)

        if job.get("needs_test") and not (test_file and os.path.exists(os.path.join(self.repo, test_file))):
            self.emit("job_needs_test", id=jid, test_file=test_file,
                      note="regresyon testi henuz yok (test-then-fix); test-job gerekli, atlaniyor")
            return {"id": jid, "outcome": "needs_test", "iters": 0}

        # 1) ilk test
        passed, out = self.run_pytest(test_file)
        self.emit("test_run", id=jid, phase="initial", passed=passed, tail=out[-600:])
        if passed:
            newstatus = "regression-watch" if job.get("status") == "regression-watch" else "green"
            job["status"] = newstatus
            self.emit("job_green", id=jid, edited=False, status=newstatus)
            return {"id": jid, "outcome": "green", "iters": 0, "edited": False}

        if self.dry_run:
            self.emit("job_dry_fail", id=jid, note="dry-run: FAIL ama duzenleme yapilmaz")
            return {"id": jid, "outcome": "dry_fail", "iters": 0}

        if not model_pipe.ollama_up():
            self.emit("job_blocked", id=jid, reason="yerel model runtime (:11434) kapali")
            job["status"] = "blocked"
            return {"id": jid, "outcome": "blocked", "iters": 0}

        # 2) fix dongusu
        max_iters = int(job.get("max_iters", 5))
        for i in range(1, max_iters + 1):
            self.emit("fix_iter", id=jid, iter=i, of=max_iters)
            current = guard.read(target)
            spec = job["fix_spec"] + "\n\n=== CURRENT FILE ===\n```python\n" + current + "\n```"
            try:
                code = model_pipe.draft_review(spec, job.get("checklist", ""),
                                               on_token=None, num_predict=4096)
            except Exception as e:
                self.emit("fix_model_error", id=jid, iter=i, error=str(e))
                continue

            ok, reason = guard.check_candidate(code, job.get("guard_needles"),
                                               job.get("forbidden_needles"))
            if not ok:
                self.emit("guard_reject", id=jid, iter=i, reason=reason)
                continue

            bak = guard.backup(target)
            guard.write(target, code)
            self.emit("splice_applied", id=jid, iter=i, backup=os.path.basename(bak))

            # 3) hedef + regresyon
            tests = [test_file] + self.regression_set(exclude_test=test_file)
            passed2, out2 = self.run_pytest(tests)
            self.emit("test_run", id=jid, phase="post_splice", iter=i, passed=passed2,
                      tests=tests, tail=out2[-800:])
            if passed2:
                gate_mode = job.get("browser_gate")
                if gate_mode:
                    gate_ok, gate_report = self._run_browser_gate(gate_mode)
                    self.emit("browser_gate", id=jid, iter=i, mode=gate_mode, ok=gate_ok, report=gate_report)
                    if not gate_ok:
                        guard.restore(target, bak)
                        self.emit("rollback", id=jid, iter=i, note="browser_gate FAIL, .bak geri yuklendi")
                        continue
                job["status"] = "green"
                self.emit("job_green", id=jid, edited=True, iter=i, backup=os.path.basename(bak))
                return {"id": jid, "outcome": "green", "iters": i, "edited": True}
            # regresyon/hedef bozuk -> geri al
            guard.restore(target, bak)
            self.emit("rollback", id=jid, iter=i, note="test gecmedi, .bak geri yuklendi")

        job["status"] = "blocked"
        self.emit("job_blocked", id=jid, reason=f"{max_iters} tur sonunda yesil degil (orijinal korundu)")
        return {"id": jid, "outcome": "blocked", "iters": max_iters}

    # ---- tum board ---------------------------------------------------------
    def run_all(self, only_job=None, only_status=None):
        t0 = time.time()
        self.emit("loop_start", dry_run=self.dry_run, jobs=len(self.board["jobs"]),
                  ollama=model_pipe.ollama_up())
        results = []
        for job in self.board["jobs"]:
            if only_job and job["id"] != only_job:
                continue
            if only_status and job.get("status") != only_status:
                continue
            results.append(self.run_job(job))
            self.save_board()
        dur = round(time.time() - t0, 1)
        self.write_kpi(results, dur)
        self.emit("loop_done", duration_s=dur,
                  green=sum(1 for r in results if r["outcome"] == "green"),
                  blocked=sum(1 for r in results if r["outcome"] == "blocked"),
                  results=results)
        return results

    def save_board(self):
        with open(self.board_path, "w", encoding="utf-8") as f:
            json.dump(self.board, f, ensure_ascii=False, indent=2)

    def write_kpi(self, results, dur):
        kpi = {
            "last_run_ts": _now(),
            "duration_s": dur,
            "jobs_run": len(results),
            "green": sum(1 for r in results if r["outcome"] == "green"),
            "blocked": sum(1 for r in results if r["outcome"] == "blocked"),
            "needs_test": sum(1 for r in results if r["outcome"] == "needs_test"),
            "iters_total": sum(r.get("iters", 0) for r in results),
            "results": results,
        }
        with open(self.kpi_path, "w", encoding="utf-8") as f:
            json.dump(kpi, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="KASA otonom test-duzelt dongusu")
    ap.add_argument("--board", default=os.path.join(HERE, "board.json"))
    ap.add_argument("--job", default=None, help="yalniz bu is id'sini kos")
    ap.add_argument("--status", default=None, help="yalniz bu statudeki isleri kos")
    ap.add_argument("--dry-run", action="store_true", help="test et ama DUZENLEME yapma")
    ap.add_argument("--py", default=DEFAULT_PY)
    args = ap.parse_args()
    runner = LoopRunner(args.board, py_exe=args.py, dry_run=args.dry_run)
    results = runner.run_all(only_job=args.job, only_status=args.status)
    blocked = sum(1 for r in results if r["outcome"] == "blocked")
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
