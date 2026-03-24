---
description: 新設計テンプレートでプラグインを作成する
---

# create-plugin スキル

新設計アーキテクチャに準拠したプラグインを自動生成します。

## 使用方法

```
/create-plugin <plugin_id> <plugin_display_name> [min_plan]
```

### パラメータ

- `plugin_id`: プラグインID（snake_case、例: `inventory_management`）
- `plugin_display_name`: 表示名（日本語可、例: `在庫管理`）
- `min_plan`: 最小利用プラン（オプション、デフォルト: `STARTER`）

### 例

```
/create-plugin inventory_management 在庫管理 STARTER
```

## 生成されるファイル

```
implementations/{plugin_id}_plugin/
├── __init__.py              # MANIFEST + Plugin クラスの再エクスポート
├── manifest.py              # PluginManifest 定義
├── plugin.py                # BasePlugin 継承（execute() オーバーライドなし）
├── config.py                # ビジネス設定のみ
├── table_definitions.py     # テーブルメタデータ
├── ddls.py                  # DDL定義
├── data_adapter_factory.py  # DataAdapterFactory
├── modules/
│   ├── __init__.py
│   └── sample.py            # サンプルモジュール
├── shared/
│   ├── __init__.py
│   ├── exceptions.py        # 例外定義
│   ├── postgresql_helper.py
│   └── snowflake_helper.py
├── tasks/
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_plugin.py
│   └── test_sample.py
└── docs/
    └── README.md
```

## 実行手順

1. 引数をパース: `$ARGUMENTS` から plugin_id, plugin_display_name, min_plan を抽出
2. PluginName を生成: plugin_id を PascalCase に変換
3. ERROR_PREFIX を生成: plugin_id の頭文字2文字を大文字に
4. server/app/plugins/implementations/{plugin_id}_plugin/ ディレクトリを作成
5. 各ファイルをテンプレートから生成（以下のテンプレートを使用）

---

## テンプレート

### __init__.py

```python
from .manifest import MANIFEST
from .plugin import {PluginName}Plugin

__all__ = ["MANIFEST", "{PluginName}Plugin"]
```

### manifest.py

```python
from app.plugins.registry import PluginManifest, PluginRegistry
from .config import default_configuration

MANIFEST = PluginManifest(
    id="{plugin_id}",
    name="{plugin_display_name}",
    description="{plugin_display_name}プラグイン",
    version="1.0.0",
    scope="ORGANIZATION",
    min_plan="{min_plan}",
    requires_configuration=True,
    default_configuration=default_configuration,
    module_path="app.plugins.implementations.{plugin_id}_plugin",
)

PluginRegistry.register_plugin(MANIFEST)
```

### plugin.py

```python
from app.plugins.executor import BasePlugin
from .modules.sample import SampleModule


class {PluginName}Plugin(BasePlugin):
    """{plugin_display_name}"""

    def __init__(self):
        super().__init__()
        self.modules = {
            "sample": SampleModule(),
        }
        self.tasks = {}
        self.legacy_action_map = {}
```

### config.py

```python
default_configuration = {
    "api_settings": {
        "max_items_per_page": 50,
    },
}
```

### table_definitions.py

```python
TABLE_DEFINITIONS = {
    "schemas": [],
}
```

### ddls.py

```python
postgresql_schema_ddls = []
snowflake_schema_ddls = []
```

### data_adapter_factory.py

```python
from app.plugins.shared.base_data_adapter_factory import BaseDataAdapterFactory
from .shared.postgresql_helper import PostgreSQLHelper
from .shared.snowflake_helper import SnowflakeHelper


class DataAdapterFactory(BaseDataAdapterFactory):
    @classmethod
    def _create_postgresql_helper(cls, organization_id, account_id):
        return PostgreSQLHelper(
            organization_id=organization_id,
            account_id=account_id,
        )

    @classmethod
    def _create_snowflake_helper(cls, organization_id, account_id):
        return SnowflakeHelper(
            organization_id=organization_id,
            account_id=account_id,
        )
```

### modules/sample.py

```python
from typing import Any, Dict, List
from app.plugins.executor import BaseSubPlugin


class SampleModule(BaseSubPlugin):
    """{plugin_display_name} サンプルモジュール"""

    @property
    def module_name(self) -> str:
        return "sample"

    @property
    def supported_actions(self) -> List[str]:
        return ["list", "create", "get", "update", "delete"]

    async def execute(self, sub_action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if sub_action not in self.supported_actions:
            return self._unsupported_action_error(sub_action)

        handler = getattr(self, f"_handle_{sub_action}", None)
        if not handler:
            return self._unsupported_action_error(sub_action)

        try:
            return await handler(context)
        except Exception as e:
            return self._execution_error(str(e), e)

    async def _handle_list(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._success_response(data={"items": []}, message="一覧取得成功")

    async def _handle_create(self, context: Dict[str, Any]) -> Dict[str, Any]:
        data = context.get("data", {})
        return self._success_response(data=data, message="作成成功")

    async def _handle_get(self, context: Dict[str, Any]) -> Dict[str, Any]:
        item_id = context.get("data", {}).get("id")
        if not item_id:
            return self._validation_error("id は必須です")
        return self._success_response(data={"id": item_id})

    async def _handle_update(self, context: Dict[str, Any]) -> Dict[str, Any]:
        data = context.get("data", {})
        return self._success_response(data=data, message="更新成功")

    async def _handle_delete(self, context: Dict[str, Any]) -> Dict[str, Any]:
        item_id = context.get("data", {}).get("id")
        return self._success_response(data={"deleted": item_id}, message="削除成功")
```

### shared/exceptions.py

```python
from app.plugins.implementations.shared.exceptions import PluginError, COMMON_ERROR_CODES


PLUGIN_ERROR_CODES = {
    **COMMON_ERROR_CODES,
    "{ERROR_PREFIX}001": "{plugin_display_name}一般エラー",
    "{ERROR_PREFIX}002": "バリデーションエラー",
}


class {PluginName}Error(PluginError):
    """{plugin_display_name}固有の例外基底クラス"""

    def __init__(self, message: str, error_code: str = "{ERROR_PREFIX}001", details=None):
        super().__init__(message, error_code=error_code, details=details)
```

### shared/postgresql_helper.py

```python
from app.repositories.postgresql_generic_repository import PostgreSQLGenericRepository


class PostgreSQLHelper:
    def __init__(self, organization_id=None, account_id=None):
        self.repo = PostgreSQLGenericRepository(
            organization_id=organization_id,
            account_id=account_id,
        )
```

### shared/snowflake_helper.py

```python
from app.repositories.snowflake_generic_repository import SnowflakeGenericRepository


class SnowflakeHelper:
    def __init__(self, organization_id=None, account_id=None):
        self.repo = SnowflakeGenericRepository(
            organization_id=organization_id,
            account_id=account_id,
        )
```

### tests/test_plugin.py

```python
import pytest
from ..plugin import {PluginName}Plugin


@pytest.fixture
def plugin():
    return {PluginName}Plugin()


@pytest.fixture
def base_context():
    return {
        "account_id": "test_account",
        "organization_id": "test_org",
        "user_id": "test_user",
        "configuration": {},
    }


class TestRouting:
    @pytest.mark.asyncio
    async def test_module_action(self, plugin, base_context):
        base_context["action"] = "sample.list"
        result = await plugin.execute(base_context)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_unknown_module(self, plugin, base_context):
        base_context["action"] = "nonexistent.list"
        result = await plugin.execute(base_context)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_unknown_action(self, plugin, base_context):
        base_context["action"] = ""
        result = await plugin.execute(base_context)
        assert result["status"] == "error"
```

### docs/README.md

```markdown
# {plugin_display_name}

## 概要

{plugin_display_name}プラグイン。

## アクション一覧

| アクション | 説明 |
|-----------|------|
| `sample.list` | 一覧取得 |
| `sample.create` | 新規作成 |
| `sample.get` | 取得 |
| `sample.update` | 更新 |
| `sample.delete` | 削除 |

## セットアップ

1. `plugins` テーブルにレコード追加
2. OrganizationPlugin で有効化
3. AccountPlugin で有効化
```

---

## 注意事項

- 生成後、必要に応じてモジュールやテーブル定義を追加してください
- テストは必ず実行してください: `pytest app/plugins/implementations/{plugin_id}_plugin/tests/ -v`
