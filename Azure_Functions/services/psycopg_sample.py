import psycopg
from db.common import get_db_connection_info

def select() -> list:
    try:
        # PostgreSQL接続情報
        db_info = get_db_connection_info()

        # PostgreSQLに接続
        conn = psycopg.connect(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            password=db_info["password"],
            dbname=db_info["dbname"]
        )

        # カーソルを作成
        cur = conn.cursor()

        # SQLクエリを実行
        cur.execute("SELECT * FROM products")

        # 結果を取得
        rows = cur.fetchall()

        # 結果を辞書のlistに変換
        products = [{"id": row[0], "name": row[1], "price": float(row[2])} for row in rows]
        return products

    finally:
        # 接続を閉じる
        cur.close()
        conn.close()

