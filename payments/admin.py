from django.contrib import admin
from payments.models import PaymentTransaction, Subscription, WebhookEvent

admin.site.register(PaymentTransaction)
admin.site.register(Subscription)   
admin.site.register(WebhookEvent)