# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_auto_20190414_2051'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='ordergoods',
            table='order_goods',
        ),
        migrations.AlterModelTable(
            name='orderinfo',
            table='order_info',
        ),
    ]
