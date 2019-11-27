.. title: [Django] モデルの verbose_name を テーブル comment に
.. slug: 2019-11-27-django-mysql-comment
.. date: 2019-11-27 09:14:00 UTC+09:00
.. tags: Django
.. category: 
.. link: 
.. description: 
.. type: text
.. has_math: true

概要
----------------------------------------------------------------------------------------------------

Django のモデルの ``verbose_name`` や フィールドの ``verbose_name`` を MySQL テーブルのコメントに追加する command を作る.

Qiita の記事([a]_) に同じ内容のものがあるが, 少し古くMySQL 用でもないため自作した.


環境
----------------------------------------------------------------------------------------------------

+ Django 2.1
+ MySQL 5.7


実装
----------------------------------------------------------------------------------------------------

コード
....................................................................................................

``<app>/management/commands/add_mysql_comments.py`` を作成

.. code-block:: python

    
    import re

    from django.core.management.base import AppCommand
    from django.db import connections


    class Command(AppCommand):
        help = 'add mysql comments'

        cursor = None

        def alter_table_comment(self, model):
            meta = model._meta
            statement = f"ALTER TABLE {meta.db_table} COMMENT '{meta.verbose_name}';"
            # statements.append(statement)
            self.cursor.execute(statement)
            return statement

        def _get_alter_column_statements_without_comment(self, table_name) -> dict:

            self.cursor.execute(f'SHOW CREATE TABLE {table_name}')
            f = self.cursor.fetchone()
            sql = f[1]
            lines = re.split(r'[\r\n]+', sql)
            columns = {}

            for line in lines:
                line = line.strip()
                m = re.match(r'^`(.*?)`[^,]*', line)
                if not m: continue
                s = m.group(0)
                # 既存コメント除外
                s = re.sub(r"COMMENT +'([^']|'')+'[ ,$]?", '', s)
                columns[m.group(1)] = s

            res = {}
            for k, v in columns.items():
                res[k] = f'alter table `{table_name}` modify {v} '
            return res

        def alter_columns_comment(self, model):
            meta = model._meta
            table_name = meta.db_table
            alter_statements = self._get_alter_column_statements_without_comment(table_name)

            statements = []

            for field in model._meta.fields:
                column = field.db_column or field.column
                statement = alter_statements.get(column, None)
                if not statement: continue

                comment = field.verbose_name
                if comment:
                    statement += f" COMMENT '{comment}'"
                    self.cursor.execute(statement)
                    statements.append(statement)

            return statements

        def handle_app_config(self, app_config, **options):
            """
            # TODO: database を指定(今 default 固定)
            # TODO: 除外モデルを指定
            """

            if app_config.models_module is None:
                return

            connection = connections['default']
            self.cursor = connection.cursor()
            models = app_config.get_models(include_auto_created=True)

            statements = []
            for model in models:
                statements.append(self.alter_table_comment(model))
                statements += self.alter_columns_comment(model)

            connection.close()  # 必要？

            return '\n'.join(statements)


使い方
....................................................................................................

``./manage.py add_mysql_comments`` のあとに, 対象の app 名を指定する. 複数の app を指定したい場合は スペース区切りで指定する.

.. code-block:: bash

    ./manage.py add_mysql_comments <app1> <app2>


テーブル確認
#################

MySQL で ``SHOW CREATE TABLE accounts_user;``

.. code-block:: sql

    CREATE TABLE `accounts_user` (
      `password` varchar(128) NOT NULL COMMENT 'パスワード',
      `last_login` datetime(6) DEFAULT NULL COMMENT '最終ログイン',
      `is_superuser` tinyint(1) NOT NULL COMMENT 'スーパーユーザー権限',
      `username` varchar(150) NOT NULL COMMENT 'ユーザー名',
      ... 以下略

となっていれば OK.
    

.. [a] https://qiita.com/44d/items/6efdb4050b3c4fb4c181 
