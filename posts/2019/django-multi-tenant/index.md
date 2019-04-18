<!--
.. title: [Django] マルチテナントやってみた
.. slug: index
.. date: 2019-04-19
.. tags: Django
.. category: 
.. link: 
.. description: Django multi tenant app
.. type: text
-->

## はじめに

1つのアプリケーションで店舗や施設, 企業ごとに独立したデータを扱いたいことは稀にあります. そんなときに使えそうなのが Multi Tenant.

[Building Multi Tenant Applications with Django — Building Multi Tenant Applications with Django 2.0 documentation](http://books.agiliq.com/projects/django-multi-tenant/en/latest/index.html)

上記サイトでは

+ 1つのスキーマ内で独立させる
+ 1つのDBで, 個別のスキーマを作り独立させる
+ DB自体 を独立させる
+ Docker を使って独立させる

方法が掲載されています. 

どれも長所短所あると思うので, 要件に応じて使い分けるべきかなという印象.

1つめの1つのスキーマ内で独立させる方法は, どうしても `店舗id` のような属性が必要になるので, そのフィルタリングを付与する方法を合わせて考えたほうが良いと思います.

今回は3つめのDB自体を独立させる方法を少しカスタマイズしつつ実装してみます.

## 要件

+ 上記サイトにならい 店舗は `thor`, `potter` があるとして, それぞれ専用の DB を用意します
+ アカウントなど他の app も DB を分けて管理します. 2つの店舗間で情報は共有されません
+ `thor.local`, `potter.local` ドメインがあるとし, アクセスに対しそれぞれ `thor` DB, `potter` DB を参照するようにします


## 環境

+ Python 3.7
+ Django 2.1
+ DB: SQLite

## 実装

[サンプルコード fumuumuf/simple_drf at multi_tenant](https://github.com/fumuumuf/simple_drf/tree/multi_tenant)

### ざっくり手順

1. middleware でアクセスされたドメインから使用するDBを判別し `threading.local` に記録
2. Database routing で 1 で記録した DB から使用する DB へルーティング

おおまかな手順はこれだけです.

### DB 設定

DB の設定をします. 2つの DB `thor`, `potter` を追加します.

後述する db routing の設定 の `DATABASE_ROUTERS` も合わせて行います.

```
# simple_drf/settings.py

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "default.sqlite3"},
    "thor": {"ENGINE": "django.db.backends.sqlite3", "NAME": "thor.sqlite3"},
    "potter": {"ENGINE": "django.db.backends.sqlite3", "NAME": "potter.sqlite3"},
}

DATABASE_ROUTERS = ['simple_drf.db_router.CustomDBRouter']
```

### middleware class

```py
# simple_drf/middleware.py

import threading

THREAD_LOCAL = threading.local()

DB_MAP = {
    'thor': 'thor',
    'potter': 'potter'
}

def get_current_db_name():
    return getattr(THREAD_LOCAL, "DB", None)


def set_db_for_router(db):
    setattr(THREAD_LOCAL, "DB", db)


def _hostname_from_request(request):
    # split on `:` to remove port
    return request.get_host().split(':')[0].lower()


def _tenant_db_from_request(request):
    hostname = _hostname_from_request(request)
    subdomain_prefix = hostname.split('.')[0]
    return DB_MAP.get(subdomain_prefix)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        db = _tenant_db_from_request(request)
        set_db_for_router(db)
        response = self.get_response(request)
        return response
```

middleware については 公式サイト [Middleware | Django documentation | Django](https://docs.djangoproject.com/en/dev/topics/http/middleware/) を参照.

アクセスがあると middleware が call されるので, 
アクセス元のドメインを元に使用する DB を選択し `THREAD_LOCAL` 
に記録しています.

#### settings.py の更新

`settings.py`
に middleware の設定を追加します.

```py
# simple_drf/settings.py


MIDDLEWARE = [
    ....

    'simple_drf.middleware.TenantMiddleware', # 追加
]
```


### db routing

Django では database routing という仕組みを使って, 使用する DB を選択できます.  [Multiple databases | Django documentation | Django](https://docs.djangoproject.com/en/dev/topics/db/multi-db/)

今回は middleware で `THREAD_LOCAL` にセットされた DB に接続するようにします.

```py

# simple_drf/db_router.py

from .middleware import get_current_db_name


class CustomDBRouter:
    """
    DB のルーティングを制御します.
    """

    def common_routing(self, model):
        db = get_current_db_name() # THREAD_LOCAL に登録された値を取得

        # print('routing db', db)
        return db

    def db_for_read(self, model, **hints):
        return self.common_routing(model)

    def db_for_write(self, model, **hints):
        return self.common_routing(model)

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations
        """
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        allow migrations
        """
        return None
```

### migration

database を指定してマイグレーションします.

```console
python manage.py migrate --database=thor 
python manage.py migrate --database=potter
```

--- 

以上でドメイン別にアクセスすると, それぞれの DB へアクセスできるようになりました.

私のサンプルコードではつぎのコマンドでユーザーを追加できるのでお試しできます.

```console
python manage.py loaddata --database thor accounts/fixtures/data.json  
python manage.py loaddata --database potter accounts/fixtures/data.json
```

### manage コマンドへの対応

すべてのコマンドに db 指定ができるわけではないので,  テナントコンテキスト管理用の `tenant_context_manage.py` を作成します.

`manage.py` の main 関数を書き換え, 第1引数で DB を指定できるようにします.

```py
# tenant_context_manage.py

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simple_drf.settings')
    try:
        from django.core.management import execute_from_command_line
        from django.core.management.commands.runserver import Command as runserver
        runserver.default_addr = "0.0.0.0"
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc


    from django.db import connection

    args = sys.argv
    db = args[1]
    with connection.cursor() as cursor:
        set_db_for_router(db)
        del args[1]
        print(args)
        execute_from_command_line(args)
```

super ユーザーの作成など, DBやデータの変更に関わるものはこの manager で行うようです.

```console
python tenant_context_manage.py thor createsuperuser --database=thor
```

## おわりに

とても簡単にマルチテナントが実現できました. (MySQL や PostgreSQL ではまだみえてない問題が発生するかもですが)

DB_MAP を default のデータベースに保存するなどで動的に接続先を変更したり, 増やしたりすることもできるようになりそうです.

### わかってないこと

今回のようにユーザー情報も含めて分離する場合,  `manage.py` で `MIDDLEWARE` の指定順を厳密にすべきなのでは？と思っています.
`AuthenticationMiddleware` よりも先に `TenantMiddleware` が実行されないと, 別のDBの認証情報が使われてしまったりしないかと懸念しています.

## 参考サイト

[Building Multi Tenant Applications with Django — Building Multi Tenant Applications with Django 2.0 documentation](http://books.agiliq.com/projects/django-multi-tenant/en/latest/index.html) 
