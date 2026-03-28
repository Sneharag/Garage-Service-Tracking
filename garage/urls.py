from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('addvehicle/', views.add_vehicle, name='add_vehicle'),
    path('vehicles', views.vehicle_list, name='vehicle_list'),
    path('vehicle/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('editvehicle/<int:pk>/', views.vehicle_edit, name='vehicle_edit'),
    path('deletevehicle/<int:pk>/', views.vehicle_delete, name='vehicle_delete'),
    path('myvehicles/', views.customer_vehicles, name='customer_vehicles'),
    path('createjob/', views.create_service_job, name='create_service_job'),
    path('servicejobs/', views.service_job_list, name='service_job_list'),
    path('mechanic/job/<int:id>/', views.update_service_job, name='update_service_job'),
    path('servicejob/<int:id>/', views.service_job_detail, name='service_job_detail'),
    path('servicejob/delete/<int:id>/', views.delete_service_job, name='delete_service_job'),
    path('mechanic/jobdetail/<int:id>/', views.mechanic_job_detail, name='mechanic_job_detail'),
    path('parts/', views.part_list, name='part_list'),
    path('parts/add/', views.add_part, name='add_part'),
    path('parts/edit/<int:pk>/', views.edit_part, name='edit_part'),
    path('parts/delete/<int:pk>/', views.delete_part, name='delete_part'),
    path('invoice/create/', views.create_invoice, name='create_invoice'),    
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/pay/<int:pk>/', views.pay_invoice, name='pay_invoice'),
    path('payment/handler/', views.payment_handler, name='payment_handler'),
    path('service-job/<int:id>/approve/', views.approve_service_job, name='approve_service_job'),
    path('service-job/<int:id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('revenueanalytics/', views.revenue_analytics, name='revenue_analytics'),
    path('ajax/get-vehicles/', views.get_customer_vehicles, name='get_customer_vehicles'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


