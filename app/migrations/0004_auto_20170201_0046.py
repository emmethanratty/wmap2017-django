# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-01 00:46
from __future__ import unicode_literals

import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20170201_0038'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
