from django.contrib import admin
from .models import Vehicle,ServiceJob,InvoicePart,Invoice

admin.site.register(Vehicle)
admin.site.register(ServiceJob)
admin.site.register(Invoice)
admin.site.register(InvoicePart)

