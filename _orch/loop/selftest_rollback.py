# -*- coding: utf-8 -*-
"""
KASA loop — rollback SELF-TEST (deterministik, model cagrisi YOK).
Sahte bir 'bozuk fix' enjekte eder: guard'i gecen (derlenir + needle var) ama testi GECMEYEN
bir cikti. Beklenen: motor splice eder -> test FAIL -> .bak'tan geri yukler -> max_iters sonunda
'blocked' + hedef dosya ORIJINAL haline donmus olur. Bu, guard+rollback mekanizmasini kanitlar.
"""
import os, sys, json, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_pipe
import loop_runner


def fake_draft_review(spec, checklist, on_token=None, num_predict=4096):
    # Derlenir + guard needle 'SENTINEL_OK' icerir ama testi GECIRMEZ.
    return "SENTINEL_OK = 1\nVALUE = 'BROKEN_FIX'\n"


def main():
    tmp = tempfile.mkdtemp(prefix="kasa_loop_selftest_")
    repo = tmp
    os.makedirs(os.path.join(repo, "src"))
    os.makedirs(os.path.join(repo, "tests"))

    target_rel = "src/target.py"
    original = "# ORIGINAL\nVALUE = 'original'\n"
    with open(os.path.join(repo, target_rel), "w", encoding="utf-8") as f:
        f.write(original)

    # Her zaman FAIL eden test (fix ne olursa olsun yesile donmez)
    test_rel = "tests/test_always_fail.py"
    with open(os.path.join(repo, test_rel), "w", encoding="utf-8") as f:
        f.write("def test_intentional_fail():\n    assert False, 'kasitli hata (rollback selftest)'\n")

    board = {
        "meta": {"repo_root": repo.replace("\\", "/"), "regression_always": []},
        "jobs": [{
            "id": "rollback-selftest", "title": "rollback", "track": "SELFTEST",
            "target_file": target_rel, "test_file": test_rel,
            "guard_needles": ["SENTINEL_OK"], "forbidden_needles": [],
            "max_iters": 2, "status": "pending",
            "fix_spec": "irrelevant", "checklist": "",
        }],
    }
    board_path = os.path.join(tmp, "board.json")
    with open(board_path, "w", encoding="utf-8") as f:
        json.dump(board, f)

    # Model katmanini sahtele (SIFIR gercek model cagrisi)
    model_pipe.draft_review = fake_draft_review
    model_pipe.ollama_up = lambda: True

    runner = loop_runner.LoopRunner(board_path)
    results = runner.run_all()

    final = open(os.path.join(repo, target_rel), encoding="utf-8").read()
    baks = [x for x in os.listdir(os.path.join(repo, "src")) if ".bak_loop_" in x]
    outcome = results[0]["outcome"]
    restored = (final == original)
    spliced_at_least_once = len(baks) >= 1

    ok = outcome == "blocked" and restored and spliced_at_least_once
    print("\n=== ROLLBACK SELF-TEST ===")
    print(f"outcome        = {outcome} (beklenen: blocked)")
    print(f"target restored= {restored} (beklenen: True — .bak geri yuklendi)")
    print(f"splice+bak     = {spliced_at_least_once} (beklenen: True — en az 1 .bak olustu)")
    print("SONUC:", "PASS" if ok else "FAIL")

    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
