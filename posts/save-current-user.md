<!--
.. title: [Django] 登録・更新ユーザーの保存
.. slug: save-current-user
.. date: 2019-04-08 02:33:06 UTC+09:00
.. tags: Django
.. category: Django
.. link: 
.. description: 作成・更新ユーザーの保存
.. type: text
-->

ログインユーザーを作成・更新ユーザーとして, モデルエンティティに記録する.  
以下パッケージが目的に合っているのでお試しする.  

[PaesslerAG/django-currentuser: Conveniently store reference to request user on thread/db level.](https://github.com/PaesslerAG/django-currentuser)


## 環境

+ Python 3.7
+ Django: 2.1
+ django-currentuser: 0.3.4


## パッケージ導入

パッケージの README にあるとおり

1. pip install

2. MIDDLEWARE に `'django_currentuser.middleware.ThreadLocalUserMiddleware'` を追加


## ユーザーの記録

これも README にあるとおり,  モデルのフィールドに `CurrentUserField` を使うだけでよい. `null`, `default`, `to` は自動でセットされるので指定してはいけない.

また, `on_delete` を指定しないと `models.CASCADE` となるので注意.

```py
# add import
from django_currentuser.db.models import CurrentUserField


class Article(models.Model):

    # ... 中略

    # verbose_name や editable はお好みでつける
    created_by = CurrentUserField(verbose_name='作成者', editable=False)
```


## 更新ユーザー

モデルの `save` メソッドで, `get_current_authenticated_user` 関数を使って更新ユーザーを記録する.


```python

# add import
from django_currentuser.middleware import get_current_authenticated_user


class Article(models.Model):

    # ... 中略

    # relation 先(User) が updated_by と同じなので, related_name 引数を追加
    created_by = CurrentUserField(verbose_name='作成者', editable=False, related_name='create_articles')

    # フィールド追加
    updated_by = CurrentUserField(verbose_name='更新者', editable=False, related_name='update_articles')

    def save(self, *args, **kwargs):
        self.updated_by = get_current_authenticated_user()
        super(Article, self).save(*args, **kwargs)

```

## サンプルコード

[simple_drf at current-user · fumuumuf/simple_drf](https://github.com/fumuumuf/simple_drf/tree/current-user/)

`articles` app の `Article` モデルに実装.
