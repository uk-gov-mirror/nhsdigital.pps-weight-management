from django.db import models

class Item(models.Model):
    item_id = models.IntegerField(primary_key=True)
    value = models.CharField(max_length=255)

    class Meta:
        db_table = "item"   # public.item
        managed = False     # table created by management command
