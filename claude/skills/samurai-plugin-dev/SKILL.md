---
name: samurai-plugin-dev
description: samurai_seller_api プラグイン開発ガイド。プラグインの新規作成、モジュール/タスク実装、バッチ設定、DDL定義時に使用。
---

# samurai_seller_api プラグイン開発ガイド

## ディレクトリ構造

```
server/app/plugins/implementations/{plugin_name}/
├── manifest.py            # [必須] メタデータ・登録
├── plugin.py              # [必須] メインクラス (BasePlugin継承)
├── config.py              # [必須] デフォルト設定
├── __init__.py            # [必須] パッケージ初期化
├── batch_config.py        # [任意] バッチスケジュール定義
├── ddls.py                # [任意] DBスキーマ定義
├── table_definitions.py   # [任意] UI用テーブルメタデータ
├── data_adapter_factory.py # [任意] DBヘルパーファクトリ
├── modules/               # [必須] 機能モジュール群
│   ├── __init__.py
│   └── {module_name}.py   # BaseSubPlugin継承
├── tasks/                 # [任意] バックグラウンドタスク群
│   ├── __init__.py
│   ├── batch.py           # バッチディスパッチャ
│   └── {task_name}.py     # BaseTask継承
└── shared/                # [任意] プラグイン固有ユーティリティ
    ├── exceptions.py
    └── postgresql_helper.py
```

---

## 必須ファイル

### 1. manifest.py

```python
"""プラグインマニフェスト"""
from app.plugins.registry import PluginManifest, PluginRegistry
from .config import default_configuration

MANIFEST = PluginManifest(
    id="{plugin_name}",                    # ディレクトリ名と一致（_plugin不要）
    name="プラグイン表示名",
    description="プラグインの説明",
    version="1.0.0",
    scope="ORGANIZATION",                  # or "ACCOUNT"
    min_plan="STARTER",                    # STARTER/PRO/ENTERPRISE
    requires_configuration=True,
    default_configuration=default_configuration,
    module_path="app.plugins.implementations.{plugin_name}_plugin",  # ディレクトリパス
)

PluginRegistry.register_plugin(MANIFEST)
```

**重要:**
- `id` はディレクトリ名から `_plugin` を除いた値（例: ディレクトリ `example_plugin` → id `example`）
- `module_path` はディレクトリのフルパス（`_plugin` 含む）

### 2. plugin.py

```python
"""プラグインメインクラス"""
from app.plugins.executor import BasePlugin
from .modules.{module_name} import {ModuleName}Module
from .tasks.{task_name}_task import {TaskName}Task

class {PluginName}Plugin(BasePlugin):
    """プラグインクラス

    クラス名: {plugin_id}をPascalCase化 + "Plugin"
    例: my_plugin → MyPluginPlugin
    """

    def __init__(self):
        super().__init__()
        self.modules = {
            "{module_name}": {ModuleName}Module(),
        }
        self.tasks = {
            "{task_name}": {TaskName}Task(),
        }
        self.legacy_action_map = {}  # 後方互換用
```

### 3. config.py

```python
"""デフォルト設定"""
default_configuration = {
    "api_settings": {
        "max_items": 50,
        "timeout_seconds": 30,
    },
    "notification_settings": {
        "enabled": True,
    },
}
```

### 4. __init__.py

```python
"""プラグインパッケージ"""
from .manifest import MANIFEST
from .plugin import {PluginName}Plugin

__all__ = ["MANIFEST", "{PluginName}Plugin"]
```

---

## モジュール実装 (modules/{module_name}.py)

```python
"""モジュール実装"""
from typing import Any, Dict, List
from app.plugins.executor import BaseSubPlugin

class {ModuleName}Module(BaseSubPlugin):
    """機能モジュール"""

    @property
    def module_name(self) -> str:
        return "{module_name}"  # modules辞書のキーと一致必須

    @property
    def supported_actions(self) -> List[str]:
        return ["list", "create", "get", "update", "delete"]

    async def execute(self, sub_action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """アクション実行"""
        if sub_action not in self.supported_actions:
            return self._unsupported_action_error(sub_action)

        handler = getattr(self, f"_handle_{sub_action}", None)
        if not handler:
            return self._unsupported_action_error(sub_action)

        try:
            return await handler(context)
        except Exception as e:
            self.logger.exception(f"Error in {sub_action}")
            return self._execution_error(str(e), e)

    async def _handle_list(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """一覧取得"""
        config = context.get("configuration", {})
        org_id = context.get("organization_id")
        account_id = context.get("account_id")

        # 実装
        items = []

        return self._success_response(
            data={"items": items, "count": len(items)},
            message="Items fetched successfully"
        )

    async def _handle_create(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """作成"""
        data = context.get("data", {})

        # バリデーション
        if not data.get("name"):
            return self._validation_error("name is required")

        # 作成処理
        new_item = {"id": 1, "name": data["name"]}

        return self._success_response(data=new_item, message="Created successfully")
```

**ヘルパーメソッド（BaseSubPlugin提供）:**
- `_success_response(data, message)` - 成功レスポンス
- `_validation_error(message, details)` - バリデーションエラー
- `_execution_error(message, exception)` - 実行エラー
- `_unsupported_action_error(action)` - 未サポートアクション

---

## タスク実装 (tasks/{task_name}_task.py)

```python
"""タスク実装"""
from typing import Dict, Any, Optional
from datetime import datetime
from app.plugins.base_task import BaseTask

class {TaskName}Task(BaseTask):
    """バックグラウンドタスク"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}

    @property
    def task_name(self) -> str:
        return "{task_name}"  # tasks辞書のキーと一致必須

    @property
    def description(self) -> str:
        return "タスクの説明"

    async def execute(
        self,
        context: Dict[str, Any],
        task_params: Dict[str, Any],
        progress_callback: Optional[Any] = None,
        is_async: bool = False,
    ) -> Dict[str, Any]:
        """タスク実行"""
        start_time = datetime.now()

        try:
            # パラメータ取得
            param1 = task_params.get("param1", "default")

            # 進捗報告
            await self._update_progress(progress_callback, "処理開始", 10)

            # メイン処理
            results = []
            total = 100
            for i in range(total):
                result = await self._process_item(i)
                results.append(result)

                progress = 10 + (i / total) * 80
                await self._update_progress(
                    progress_callback,
                    f"処理中 {i+1}/{total}",
                    int(progress)
                )

            await self._update_progress(progress_callback, "完了", 100)

            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            return {
                "task_name": self.task_name,
                "status": "completed",
                "total_execution_time_seconds": total_time,
                "results": results,
            }

        except Exception as e:
            self.logger.exception("Task execution failed")
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            return self._create_error_response(str(e), total_time)

    async def _process_item(self, index: int) -> Dict[str, Any]:
        """個別アイテム処理"""
        return {"item_id": index, "status": "processed"}
```

---

## バッチ設定 (batch_config.py)

```python
"""バッチスケジュール定義"""
batch_schedules = {
    "{task_name}_daily": {
        "description": "毎日06:00 JSTに実行",
        "cron": "0 6 * * ? *",           # AWS EventBridge形式
        "timezone": "Asia/Tokyo",
        "enabled_by_default": True,
        "max_retries": 2,
        "timeout_seconds": 600,
        "short_name": "{task_name}",
        "parameters": {
            "param1": "value1",
        },
    },
}
```

**Cron形式:** `分 時 日 月 曜日 年`（AWS EventBridge形式、`?`使用可）

---

## バッチディスパッチャ (tasks/batch.py)

```python
"""バッチ実行ディスパッチャ"""
import logging
from typing import Any, Dict, Type
from app.schemas.batch import BatchExecutionContext
from .{task_name}_task import {TaskName}Task

logger = logging.getLogger(__name__)


class {TaskName}Batch:
    """タスクをバッチ実行するラッパー"""

    def __init__(self) -> None:
        self.task = {TaskName}Task()

    async def execute(self, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        params = parameters or {}
        return await self.task.execute(
            context={},
            task_params=params,
            progress_callback=None,
            is_async=False,
        )


# バッチレジストリ: batch_config.py のキー → Batchクラス
BATCH_REGISTRY: Dict[str, Type[Any]] = {
    "{task_name}_daily": {TaskName}Batch,
}


async def execute_batch(context: BatchExecutionContext) -> Dict[str, Any]:
    """バッチ実行ディスパッチャ（batch_service.pyから呼ばれる）"""
    params = context.parameters or {}

    batch_cls = BATCH_REGISTRY.get(context.task_type)
    if batch_cls is None:
        return {
            "status": "error",
            "reason": f"unknown task_type: {context.task_type}",
            "task_type": context.task_type,
        }

    try:
        batch = batch_cls()
        logger.info("バッチ実行開始", extra={"task_type": context.task_type})
        result = await batch.execute(params)
        logger.info("バッチ実行完了", extra={"task_type": context.task_type})
        return result
    except Exception as exc:
        logger.exception("バッチ実行エラー", extra={"task_type": context.task_type})
        return {
            "status": "error",
            "reason": str(exc),
            "task_type": context.task_type,
        }
```

**重要:** `BATCH_REGISTRY`のキーは`batch_config.py`のスケジュールキーと一致必須

---

## DDL定義 (ddls.py)

```python
"""データベーススキーマ定義"""

postgresql_schema_ddls = [
    {
        "table_name": "items",
        "ddl": """
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            organization_id UUID NOT NULL,
            account_id UUID NOT NULL
        )
        """,
        "description": "アイテムマスタ",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_items_org ON items(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)",
        ],
    },
]

snowflake_schema_ddls = [
    {
        "table_name": "items",
        "ddl": """
        CREATE TABLE IF NOT EXISTS ITEMS (
            ID NUMBER AUTOINCREMENT PRIMARY KEY,
            NAME VARCHAR(255) NOT NULL,
            STATUS VARCHAR(50) DEFAULT 'active',
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            ORGANIZATION_ID VARCHAR(36) NOT NULL,
            ACCOUNT_ID VARCHAR(36) NOT NULL
        )
        """,
        "description": "アイテムマスタ",
        "indexes": [],
    },
]
```

---

## アクション呼び出しパターン

### モジュールアクション
```
POST /plugins/{plugin_id}/execute
{
    "action": "{module_name}.{sub_action}",
    "data": {...}
}
```

### タスク実行
```
POST /plugins/{plugin_id}/execute
{
    "action": "task:{task_name}",
    "task_params": {...}
}
```

### 非同期タスク実行
```
POST /plugins/{plugin_id}/execute-async
{
    "action": "task:{task_name}",
    "task_params": {...}
}
```

---

## よくある間違い

| 間違い | 正しい方法 |
|--------|------------|
| `id` と ディレクトリ名の不一致 | `id="example"` → ディレクトリ `example_plugin` |
| `module_name` と `modules` キーの不一致 | 両方同じ値を使用 |
| `task_name` と `tasks` キーの不一致 | 両方同じ値を使用 |
| `BATCH_REGISTRY` キーと `batch_config` キーの不一致 | 両方同じ値を使用 |
| `async def` で `await` 忘れ | 全ての非同期呼び出しに `await` |
| エラー時に traceback をレスポンスに含める | `logger.exception()` でログのみ、レスポンスには含めない |
| context キーの存在確認なし | `context.get("key", default)` を使用 |

---

## クイックスタートチェックリスト

新規プラグイン作成時:

- [ ] ディレクトリ作成: `implementations/{plugin_name}_plugin/`
- [ ] `manifest.py` - PluginManifest + PluginRegistry.register_plugin()
- [ ] `plugin.py` - BasePlugin継承、modules/tasks定義
- [ ] `config.py` - default_configuration
- [ ] `__init__.py` - MANIFEST, PluginClassエクスポート
- [ ] `modules/__init__.py` + モジュールファイル
- [ ] (任意) `tasks/__init__.py` + タスクファイル + `batch.py`
- [ ] (任意) `batch_config.py` - バッチスケジュール
- [ ] (任意) `ddls.py` - DBスキーマ
- [ ] 構文チェック: `python -m py_compile *.py`
- [ ] Docker内インポートテスト

---

## リファレンス実装

`server/app/plugins/implementations/example_plugin/` を参照
