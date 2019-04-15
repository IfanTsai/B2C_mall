# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='goods',
            table='goods',
        ),
        migrations.AlterModelTable(
            name='goodsimage',
            table='goods_image',
        ),
        migrations.AlterModelTable(
            name='goodssku',
            table='goods_sku',
        ),
        migrations.AlterModelTable(
            name='goodstype',
            table='goods_type',
        ),
        migrations.AlterModelTable(
            name='indexgoodsbanner',
            table='index_banner',
        ),
        migrations.AlterModelTable(
            name='indexpromotionbanner',
            table='index_promotion',
        ),
        migrations.AlterModelTable(
            name='indextypegoodsbanner',
            table='index_type_goods',
        ),
    ]
