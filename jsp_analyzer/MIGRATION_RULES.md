# Migration Rules カスタマイズガイド

JSP Analyzer では、`jsp_analyzer.py` 内の `DEFAULT_MIGRATION_RULES` を編集することで、JSPファイルから「どのようなコードを見つけたら警告（移行対象）としてレポートするか」を柔軟にカスタマイズできます。

プロジェクト固有のコーディング規約や移行方針に合わせて、不要なルールを削除したり、独自のルールを追加したりすることが可能です。

## ルールの基本構成

ルールは1つずつ辞書（`dict`形式）で定義します。
各ルールには以下のプロパティを指定できます。

| プロパティ名 | 必須 | 説明 |
| :--- | :--- | :--- |
| **`id`** | 必須 | ルールの一意な識別子。（集計時などに使用されます） |
| **`name`** | 必須 | ルールの名称。 |
| **`complexity`** | 必須 | 「高」「中」「低」など、修正の難易度や重要度。 |
| **`target`** | 必須 | **最も重要な設定項目。** 解析のどの部分を対象とするか（後述）。 |
| **`description`**| 必須 | どう修正すべきかのアドバイスなど、警告の詳細な説明。 |
| **`pattern`** | 任意 | 正規表現の文字列。指定した場合は、対象の文字列がこの正規表現にマッチした場合のみ警告とします。 |
| **`type`** | 任意 | `target` が `jsp-logic` の場合に、さらに種類（スクリプトレット、宣言、式）を限定するために使用します。 |

---

## 🎯 `target` の種類とチェックされる内容

`target` に何を指定するかで、JSPの「どの部分」がルール判定の対象になるかが決まります。ここで抽出された文字列に対して、`pattern`（正規表現）の判定が行われます。

| `target` で指定する文字 | どこがチェックされるか | `pattern` の判定対象になる文字列の例 |
| :--- | :--- | :--- |
| **`html_tag`** | すべてのHTMLタグ（およびそのタグ名） | **タグ名** (例: `font`, `div`, `form:input`, `c:if`) |
| **`html_attr_name`** | すべてのタグの全属性名 | **属性名** (例: `checked`, `disabled`, `readonly`) |
| **`html_attr_value`** | すべてのタグの全属性値 | **属性値** (例: `javascript:void(0)`, `text/javascript`) |
| **`jsp-logic`** | JSPの `<% %>` サブシステム全般 | `pattern` の判定対象にはなりません。代わりに `type` を指定します。 |
| **`el_expression`** | `${ }` などで書かれたEL式の値 | **EL式の文字列** (例: `${user.name == 'admin'}`) |
| **`inline_event`** | HTMLタグに直接書かれたイベント属性 | **イベント名と内容** (例: `onclick='doSomething()'`) |
| **`js_function`** | `<script>`内の関数定義 | **関数名** (例: `doSomething`) |
| **`js_event`** | `<script>`内のイベントバインド（`addEventListener`等） | **イベントバインドの式** (例: `window.onload → init`) |

### ⚠️ `html_tag` をターゲットにする際の重要な注意点

BeautifulSoup（内部のHTMLパーサー）の仕様により、**タグ名や属性名はすべて「小文字」に変換された状態で解析・判定されます。**

そのため、Spring FormタグやJSTLタグのように大文字・小文字が混ざっているタグ（キャメルケース等）を `pattern` で検知したい場合は、**正規表現をすべて小文字で指定する必要があります。**

*   **誤**: `r"^form:errors$"` （マッチしません）
*   **正**: `r"^form:errors$"` （あ、そもそも `errors` は小文字ですね）
*   **誤**: `r"^c:forEach$"` （マッチしません）
*   **正**: `r"^c:foreach$"` （小文字にして定義する）

---

## カスタマイズの具体例

### 1. 非推奨タグの警告を追加する

古いHTMLタグ（`<b>` や `<i>`）を利用している箇所に警告を出します。
対象はタグ名なので、`target` は `html_tag` です。

```python
{
    "id": "deprecated_style_tag",
    "name": "スタイル系HTMLタグ",
    "complexity": "低",
    "target": "html_tag",
    "pattern": r"^(b|i|u|strike)$",
    "description": "CSSのfont-weightやfont-styleへ移行してください",
}
```

### 2. 特定のSpring Formタグだけを警告する

バックエンドでのバリデーション移行に伴い、`<form:errors>` を使っている箇所を特定したい場合。
※繰り返しになりますが、タグ名は**小文字**で正規表現に指定します。

```python
{
    "id": "spring_form_errors",
    "name": "Spring Formエラー表示",
    "complexity": "中",
    "target": "html_tag",
    "pattern": r"^form:errors$",   # ← すべて小文字で指定
    "description": "React/Vue側のバリデーションエラー表示コンポーネントに移行してください",
}
```

### 3. EL式内で特定のメソッド呼び出しをしているものを警告する

EL式の中で `.clone()` やその他のJava由来のコレクション操作などを行っている箇所を見つけます。
対象はEL式なので、`target` は `el_expression` です。

```python
{
    "id": "method_call_el",
    "name": "EL式内のメソッド呼び出し",
    "complexity": "高",
    "target": "el_expression",
    "pattern": r"\.clone\(",
    "description": "JSP側での処理ではなく、バックエンドのController等で処理するように移行してください",
}
```

### 4. `<%= %>` (JSP式 / Expression) のみを警告パターンに分ける

`jsp-logic` は `pattern` ではなく、`type` プロパティを使って種別（`scriptlet`(`<% %>`), `declaration`(`<%! %>`), `expression`(`<%= %>`) のいずれか）を絞り込みます。

```python
{
    "id": "jsp_expression",
    "name": "JSP Expression",
    "complexity": "中",
    "target": "jsp-logic",
    "type": "expression",   # <% %> レベルの中で <%= %> のみに絞り込む
    "description": "直接的な出力。JSフレームワークのデータバインディング記法へ移行が必要",
}
```

### 5. React移行で問題になるBoolean属性を検出する

`checked`, `disabled`, `selected` などのBoolean属性は、Reactでは `checked={true}` のような動的バインディングに書き換える必要があります。
対象は属性名なので、`target` は `html_attr_name` です。

```python
{
    "id": "boolean_attr",
    "name": "Boolean属性",
    "complexity": "低",
    "target": "html_attr_name",
    "pattern": r"^(checked|disabled|readonly|selected|multiple)$",
    "description": "React/Vueでは動的バインディング(props)への書き換えが必要",
}
```

### 6. `javascript:` 疑似URLを検出する

`href="javascript:void(0)"` のようなレガシーな記述を検出します。
対象は属性値なので、`target` は `html_attr_value` です。

```python
{
    "id": "javascript_pseudo_url",
    "name": "JavaScript疑似URL",
    "complexity": "低",
    "target": "html_attr_value",
    "pattern": r"javascript:",
    "description": "イベントハンドラまたはRouter遷移への書き換えが必要",
}
```

