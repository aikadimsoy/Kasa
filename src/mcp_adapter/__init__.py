# kasa/src/mcp_adapter/__init__.py
# Gercek MCP (Model Context Protocol) adaptoru — ayri stdio sureci.
# KASA'nin REST sunucusunu DEGISTIRMEZ; tools/call'i /v1/execute_tool'a proxyler.
# Boylece mevcut authz (bearer + PUBLIC_TOOLS + rezerve-id + deny-by-default izinler)
# aynen devrede kalir. Calistir: py -3.12 -m src.mcp_adapter
# Bagimlilik: resmi `mcp` SDK (MIT) — yalniz bu surec; exe'ye paketlenmez.
