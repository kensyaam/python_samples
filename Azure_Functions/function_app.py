import logging

import azure.functions as func

from api.blueprint import blueprint

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(blueprint)


logging.getLogger().setLevel(logging.DEBUG)  # 全体のログレベルをDEBUGに設定

# ログレベルを含めるフォーマットを設定
fmt = "[%(levelname)s]%(message)s"
for h in logging.getLogger().handlers:  # Functions ホストが先に追加した StreamHandler
    h.setFormatter(logging.Formatter(fmt))
