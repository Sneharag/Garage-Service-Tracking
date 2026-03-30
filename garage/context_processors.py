from .models import Part, ServiceJob, Invoice
from django.db.models import F

def notifications(request):
    # If user is not logged in, don't do anything
    if not request.user or not request.user.is_authenticated:
        return {'notif_count': 0}

    try:
        # 1. ADMIN LOGIC
        if request.user.role == 'admin':
            low_stock = Part.objects.filter(quantity__lte=F('low_stock_threshold'))
            return {
            'notif_count': low_stock.count(),
            'notif_list': low_stock[:5],
            'notif_role': 'admin'
            }

        # 2. MECHANIC LOGIC
        elif request.user.role == 'mechanic':
            # Jobs assigned to them that are approved by customer but not yet started by mechanic
            approved_jobs = ServiceJob.objects.filter(
                mechanic=request.user,
                is_approved=True,
                status='pending',
                is_active=True
            )
            return {
            'notif_count': approved_jobs.count(),
            'notif_list': approved_jobs[:5],
            'notif_role': 'mechanic'
            }

        # 3. CUSTOMER LOGIC
        elif request.user.role == 'customer':
            # Jobs waiting for this customer to click 'Approve'
            pending_approval = ServiceJob.objects.filter(
                customer=request.user,
                is_approved=False,
                is_active=True
            )

            # Invoices that need payment
            unpaid_invoices = Invoice.objects.filter(
                service_job__customer=request.user,
                payment_status='unpaid'
            )

            combined_list = []
            for job in pending_approval:
                combined_list.append({
                    'type': 'approval',
                    'id': job.id,
                    'title': 'Approval Needed',
                    'desc': str(job.vehicle) # Ensure it's a string
                })

            for inv in unpaid_invoices:
                combined_list.append({
                    'type': 'invoice',
                    'id': inv.id,
                    'title': 'New Invoice',
                    'desc': f"Invoice #{inv.id}"
                })

            return {
                'notif_count': len(combined_list),
                'notif_list': combined_list[:5],
                'notif_role': 'customer'
            }

    except Exception as e:
        # If there is a database error, return 0 so the site doesn't crash
        print(f"Notification Error: {e}")
        return {'notif_count': 0}

    return {'notif_count': 0}