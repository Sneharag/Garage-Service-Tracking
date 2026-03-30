from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VehicleForm,ServiceJobForm,PartForm,InvoiceForm,InvoicePartForm
from .models import Vehicle,ServiceJob,Part,Invoice,InvoicePart,Payment
from accounts.models import User
from django.db.models import F,Sum,Q
from datetime import timedelta,datetime
from django.utils.timezone import now
import json
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models.functions import TruncMonth
from collections import defaultdict


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Fetch the latest 6 high-rated feedbacks that are not empty
    testimonials = ServiceJob.objects.filter(
        rating__gte=4
    ).exclude(
        feedback__isnull=True
    ).exclude(
        feedback=''
    ).order_by('-updated_at')[:6]

    return render(request, 'home.html', {'testimonials': testimonials})

def services(request):
    return render(request,'services.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    if request.method == "POST":
        # Handle form submission (e.g., send email or save to DB)
        return render(request, 'contact.html', {'success': True})
    return render(request, 'contact.html')

@login_required
def dashboard(request):
    user = request.user
    if user.role == 'admin' or user.is_superuser:
        total_vehicles = Vehicle.objects.count()
        total_customers = User.objects.filter(role='customer').count()
        total_jobs = ServiceJob.objects.filter(is_active=True).count()
        low_stock_parts = Part.objects.filter(quantity__lte=F('low_stock_threshold'))
        low_stock_count = low_stock_parts.count()
        recent_jobs = ServiceJob.objects.filter(is_active=True).order_by('-created_at')[:3]

        # job status counts for pie chart
        pending_jobs = ServiceJob.objects.filter(status='pending', is_active=True).count()
        inprogress_jobs = ServiceJob.objects.filter(status='in_progress', is_active=True).count()
        completed_jobs = ServiceJob.objects.filter(status='completed', is_active=True).count()

        # weekly jobs for bar chart
        today = now().date()
        week_labels = []
        week_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = ServiceJob.objects.filter(created_at__date=day).count()
            week_labels.append(day.strftime('%a'))
            week_data.append(count)

        paid_invoices = Invoice.objects.filter(payment_status='paid')

        # 2. Sum Labour Charges
        labour_sum = paid_invoices.aggregate(Sum('labour_charge'))['labour_charge__sum'] or 0

        # 3. Sum Parts (Quantity from InvoicePart * Unit Price from Part table)
        parts_sum = InvoicePart.objects.filter(invoice__in=paid_invoices).aggregate(
            total=Sum(F('quantity_used') * F('part__unit_price'))
        )['total'] or 0

        total_revenue = labour_sum + parts_sum


        return render(request, 'admin_dashboard.html', {
        'total_vehicles': total_vehicles,
        'total_customers': total_customers,
        'total_jobs': total_jobs,
        'low_stock_parts': low_stock_parts,
        'low_stock_count': low_stock_count,
        'recent_jobs': recent_jobs,
        'pending_jobs': pending_jobs,
        'inprogress_jobs': inprogress_jobs,
        'completed_jobs': completed_jobs,
        'week_labels': json.dumps(week_labels),
        'week_data': json.dumps(week_data),
        'total_revenue': total_revenue,
        })
    elif user.role == 'customer':
        vehicles = Vehicle.objects.filter(customer=user)
        jobs = ServiceJob.objects.filter(customer=user, is_active=True)

        pending_jobs = jobs.filter(status='pending').count()
        inprogress_jobs = jobs.filter(status='in_progress').count()
        completed_jobs = jobs.filter(status='completed').count()
        active_jobs = jobs.exclude(status='completed').count()

        recent_jobs = jobs.order_by('-created_at')[:5]

        context = {
            'total_vehicles': vehicles.count(),
            'total_jobs': jobs.count(),
            'active_jobs': active_jobs,
            'jobs': recent_jobs,
            'pending_jobs': pending_jobs,
            'inprogress_jobs': inprogress_jobs,
            'completed_jobs': completed_jobs,
        }
        return render(request, 'customer_dashboard.html', context)
    
    elif user.role == 'mechanic':

        jobs = ServiceJob.objects.filter(mechanic=user, is_active=True)

        total_jobs = jobs.count()
        pending_jobs = jobs.filter(status='pending').count()
        inprogress_jobs = jobs.filter(status='in_progress').count()
        completed_jobs = jobs.filter(status='completed').count()

        context = {
            'jobs': jobs.order_by('-created_at'),
            'total_jobs': total_jobs,
            'pending_jobs': pending_jobs,
            'inprogress_jobs': inprogress_jobs,
            'completed_jobs': completed_jobs,
        }

        return render(request, 'mechanic_dashboard.html', context)

    # ================= DEFAULT =================
    return redirect('home')

@login_required
def add_vehicle(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)

        # If user is a customer, we force the customer field to them
        if request.user.role == 'customer':
            if 'customer' in form.fields:
                form.fields.pop('customer',None)

        if form.is_valid():
            vehicle = form.save(commit=False)
            if request.user.role == 'customer':
                vehicle.customer = request.user
            # If Admin, the customer is already in form.cleaned_data['customer']
            vehicle.save() # CRUCIAL: Ensure this is called

            if request.user.role == 'customer':
                return redirect('customer_vehicles')
            else:
                return redirect('vehicle_list')
        else:
            # If form is NOT valid, we don't redirect.
            # We fall through to the render below which will show errors.
            print(form.errors)
    else:
        form = VehicleForm()
        if request.user.role == 'customer':
            
            form.fields.pop('customer',None)

    return render(request, 'add_vehicle.html', {'form': form})

from django.http import JsonResponse

@login_required
def get_customer_vehicles(request):
    customer_id = request.GET.get('customer_id')
    vehicles = Vehicle.objects.filter(customer_id=customer_id).values('id', 'vehicle_number', 'model')
    return JsonResponse(list(vehicles), safe=False)


@login_required
def vehicle_list(request):
    vehicles=Vehicle.objects.all().order_by('-id')
    return render(request,'vehicle_list.html',{'vehicles':vehicles})

@login_required
def vehicle_detail(request, pk):

    user = request.user
    if user.role == 'admin':
        vehicle = get_object_or_404(Vehicle, pk=pk)

    elif user.role == 'customer':
        vehicle = get_object_or_404(Vehicle, pk=pk, customer=user)

    else:
        return redirect('dashboard')

    jobs = ServiceJob.objects.filter(vehicle=vehicle)
    return render(request, 'vehicle_detail.html', {
                            'vehicle': vehicle,
                            'jobs': jobs
                            })
    
@login_required
def vehicle_edit(request, pk):
    if request.user.role == 'admin':
        vehicle = get_object_or_404(Vehicle, pk=pk)
    elif request.user.role == 'customer':
        vehicle = get_object_or_404(Vehicle, pk=pk, customer=request.user)
    else:
        return redirect('dashboard')

    form = VehicleForm(request.POST or None, instance=vehicle)
    if form.is_valid():
        form.save()
        if request.user.role == 'admin':
            return redirect('vehicle_list')
        return redirect('customer_vehicles')

    return render(request, 'add_vehicle.html', {'form': form})

@login_required
def vehicle_delete(request, pk):
    if request.user.role == 'admin':
        vehicle = get_object_or_404(Vehicle, pk=pk)
        vehicle.delete()
        return redirect('vehicle_list')
    elif request.user.role == 'customer':
        vehicle = get_object_or_404(Vehicle, pk=pk, customer=request.user)
        vehicle.delete()
        return redirect('customer_vehicles')
    else:
        return redirect('dashboard')

@login_required
def customer_vehicles(request):
    vehicles = Vehicle.objects.filter(customer=request.user).order_by('-id')
    return render(request, 'customer_vehicles.html', {'vehicles': vehicles})

@login_required
def create_service_job(request):
    if request.user.role != 'admin':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ServiceJobForm(request.POST)

        # We manually get the vehicle from the AJAX dropdown
        vehicle_id = request.POST.get('vehicle')

        if form.is_valid() and vehicle_id:
            job = form.save(commit=False)

            # Link the vehicle object
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            job.vehicle = vehicle

            # Automatically assign the customer based on the vehicle's owner
            job.customer = vehicle.customer

            job.save()
            return redirect('service_job_list')
        
    else:
        form = ServiceJobForm()

        # Get all customers for the first dropdown
    customers = User.objects.filter(role='customer')

    return render(request, 'create_service_job.html', {
    'form': form,
    'customers': customers
    })


@login_required
def service_job_list(request):
    user = request.user

    # 1. Base QuerySet based on role
    if user.role == 'admin' or user.is_superuser:
        jobs = ServiceJob.objects.filter(is_active=True)
    elif user.role == 'mechanic':
        jobs = ServiceJob.objects.filter(mechanic=request.user, is_active=True)
    elif user.role == 'customer':
        jobs = ServiceJob.objects.filter(customer=request.user, is_active=True)
    else:
        jobs = ServiceJob.objects.none()

    # 2. Get Search and Filter Parameters
    query = request.GET.get('q')
    status_filter = request.GET.get('status')

    # 3. Apply Search Logic (Vehicle Number, Customer, or Description)
    if query:
        jobs = jobs.filter(
            Q(vehicle__vehicle_number__icontains=query) |
            Q(customer__username__icontains=query) |
            Q(problem_description__icontains=query)
        )

    # 4. Apply Status Filter
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    # 5. Apply Ordering
    jobs = jobs.order_by('-created_at')

    return render(request, 'service_job_list.html', {
    'jobs': jobs,
    'search_query': query,
    'status_filter': status_filter
    })


@login_required
def service_job_detail(request, id):

    # Use get_object_or_404 for safety
    job = get_object_or_404(ServiceJob, id=id)

    # 🛡️ AUTO-FIX: If job is completed but dates are blank, generate them now
    if job.status == 'completed' and not job.warranty_expiry:
        # Use today's date as the baseline
        today = now().date()
        job.warranty_expiry = today + timedelta(days=90)   # 3 Months
        job.next_service_date = today + timedelta(days=180) # 6 Months
        job.save() # Save the fixed dates to the database

    return render(request, 'service_job_detail.html', {'job': job})

@login_required
def update_service_job(request, id):
    job = get_object_or_404(ServiceJob, id=id)
    user = request.user

    # Permission check
    if user.role not in ['admin', 'mechanic']:
        return redirect('dashboard')

    if request.method == 'POST':
        # 1. Handle Status (Will be None if field is disabled in HTML)
        new_status = request.POST.get('status')
        if new_status:
            job.status = new_status

            # 2. Handle Mechanic Notes (This should always save)
        job.mechanic_notes = request.POST.get('mechanic_notes')

            # 3. Handle Image Upload
        if 'service_image' in request.FILES:
            job.service_image = request.FILES['service_image']

        # Save Estimated Completion
        est_time = request.POST.get('estimated_completion')
        if est_time:
            job.estimated_completion = est_time

        if user.role == 'admin':
            # 1. Reassign Vehicle if changed
            vehicle_id = request.POST.get('vehicle')
            if vehicle_id:
                job.vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

            # 2. Reassign Mechanic if changed
            mechanic_id = request.POST.get('mechanic')
            if mechanic_id:
                # Assign the new mechanic
                job.mechanic = get_object_or_404(User, pk=mechanic_id)
            else:
                # Handle the "No Mechanic Assigned" option
                job.mechanic = None

            # 3. Update Problem Description if changed
            job.problem_description = request.POST.get('problem_description')

        if new_status == 'completed':
            # ✅ Change: Check if the date is NOT set yet
            if not job.warranty_expiry:
                # Use today's date for a fresh completion
                base_date = now().date()

                # Set Warranty for 90 days from today
                job.warranty_expiry = base_date + timedelta(days=90)

                # Set Next Service recommendation for 180 days (6 months)
                job.next_service_date = base_date + timedelta(days=180)
                        # 4. Save everything to Database
        job.save()

                # 5. Message for feedback
        messages.success(request, "Service job updated successfully.")

                # 6. Redirect to the DETAIL page so the mechanic can see their saved work
        return redirect('service_job_detail', id=job.id)

            # GET Request: Pass details to template
    mechanics = User.objects.filter(role='mechanic')
    vehicles = Vehicle.objects.all()
    return render(request, 'update_service_job.html', {
            'job': job,
            'user_role': user.role,
            'mechanics': mechanics,
            'vehicles': vehicles,
        })


@login_required
def approve_service_job(request, id):
    # Only the customer assigned to this job can approve it
    job = get_object_or_404(ServiceJob, id=id, customer=request.user)

    if request.method == 'POST':
        job.is_approved = True
        job.save()
        messages.success(request, "Repair work has been approved. The mechanic will start working shortly.")

        return redirect('service_job_detail', id=id)

@login_required
def mechanic_job_detail(request, id):

    if request.user.role != 'mechanic':
        return redirect('dashboard')

    job = get_object_or_404(ServiceJob, id=id, mechanic=request.user)
    return render(request, 'mechanic_job_detail.html', {'job': job})

@login_required
def delete_service_job(request, id):

    if request.user.role != 'admin':
        return redirect('dashboard')

    job = get_object_or_404(ServiceJob, id=id)
    job.is_active = False
    job.save()

    return redirect('service_job_list')

@login_required
def add_part(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        form = PartForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('part_list')
    else:
        form = PartForm()
    return render(request, 'add_part.html', {'form': form})

@login_required
def part_list(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    parts = Part.objects.all().order_by('-id')
    # "quantity is less than or equal to low_stock_threshold". F() is special — it lets you compare two fields of the same model against each other
    low_stock = parts.filter(quantity__lte=F('low_stock_threshold'))
    return render(request, 'part_list.html', {
    'parts': parts,
    'low_stock': low_stock
})

@login_required
def edit_part(request, pk):
    if request.user.role != 'admin':
        return redirect('dashboard')
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        form = PartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            return redirect('part_list')  # ✅ missing before
    else:
        form = PartForm(instance=part)
    return render(request, 'add_part.html', {'form': form})
        
@login_required
def delete_part(request, pk):
    if request.user.role != 'admin':
        return redirect('dashboard')
    part = get_object_or_404(Part, pk=pk)
    part.delete()
    return redirect('part_list')


@login_required
def create_invoice(request):
    if request.user.role != 'admin':
        return redirect('dashboard')

    # 1. Get the job_id from the URL if it exists (?job_id=5)
    selected_job_id = request.GET.get('job_id')

    # 2. Filter completed jobs that DON'T have an invoice yet
    jobs = ServiceJob.objects.filter(status='completed').exclude(invoice__isnull=False)
    parts = Part.objects.all()

    if request.method == 'POST':
        # Safely get job_id from the submitted form data
        job_id = request.POST.get('job')

        if not job_id:
            # Handle case where no job was selected
            form = InvoiceForm(request.POST)
            return render(request, 'create_invoice.html', {'form': form, 'jobs': jobs, 'parts': parts, 'error': 'Please select a job.'})

        job = get_object_or_404(ServiceJob, id=job_id)
        form = InvoiceForm(request.POST)

        if form.is_valid():
            # 3. Save the Invoice
            invoice = form.save(commit=False)
            invoice.service_job = job
            invoice.save()

            # 4. Process Parts (Moved INSIDE the is_valid block)
            part_ids = request.POST.getlist('part')
            quantities = request.POST.getlist('quantity_used')

            for part_id, qty in zip(part_ids, quantities):
                if part_id and qty:
                    try:
                        part = Part.objects.get(id=part_id)
                        qty = int(qty)
                        if part.quantity >= qty:
                            part.quantity -= qty
                            part.save()
                            InvoicePart.objects.create(
                                invoice=invoice,
                                part=part,
                                quantity_used=qty
                            )
                    except (Part.DoesNotExist, ValueError):
                        continue # Skip if part not found or qty is invalid

                    # 5. Success! Redirect to the detail page
            return redirect('invoice_detail', pk=invoice.pk)

    else:
        form = InvoiceForm()

        return render(request, 'create_invoice.html', {
                        'form': form,
                        'jobs': jobs,
                        'parts': parts,
                        'selected_job_id': selected_job_id
                    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # admin sees all, customer sees only their own
    if request.user.role == 'customer':
        if invoice.service_job.customer != request.user:
            return redirect('dashboard')

    return render(request, 'invoice_detail.html', {'invoice': invoice})

@login_required
def invoice_list(request):
    if request.user.role == 'admin':
        invoices = Invoice.objects.all().order_by('-created_at')
    elif request.user.role == 'customer':
        invoices = Invoice.objects.filter(service_job__customer=request.user).order_by('-created_at')
    else:
        return redirect('dashboard')

    return render(request, 'invoice_list.html', {'invoices': invoices})


# Initialize the Razorpay Client
razor_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def pay_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Razorpay works in Paise (1 INR = 100 Paise)
    amount_in_paise = int(invoice.grand_total() * 100)

    # Step 1: Create an Order on Razorpay Server
    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"inv_{invoice.id}",
    }
    razorpay_order = razor_client.order.create(data=data)

    # Step 2: Save this order in our database
    Payment.objects.create(
    invoice=invoice,
    razorpay_order_id=razorpay_order['id'],
    amount=invoice.grand_total()  # <--- Add () to get the number
)

    context = {
        'invoice': invoice,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': amount_in_paise,
    }
    return render(request, 'pay_invoice.html', context)


@csrf_exempt
def payment_handler(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        try:
            # Verify Signature
            razor_client.utility.verify_payment_signature(params_dict)

            # 1. Update Payment Record
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.status = 'Success'
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.save()

            # 2. Update Invoice Status
            invoice = payment.invoice
            invoice.payment_status = 'paid'
            invoice.save()

            storage = messages.get_messages(request)
            storage.used = True # This clears any existing "stuck" messages
            # 3. Add a success message for the user
            messages.success(request, f"Payment of ₹{invoice.grand_total()} was successful! Your invoice is now marked as Paid.")

            # 4. REDIRECT to the Invoice Detail page
            return redirect('invoice_detail', pk=invoice.pk)

        except Exception as e:
            # If verification fails
            messages.error(request, "Payment verification failed. Please contact support if the amount was deducted.")
            return redirect('invoice_list')
        
@login_required
def submit_feedback(request, id):
    job = get_object_or_404(ServiceJob, id=id, customer=request.user)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback')

        if rating:
            job.rating = rating
            job.feedback = feedback
            job.save()
            messages.success(request, "Thank you for your feedback!")

    return redirect('service_job_detail', id=id)

@login_required
def revenue_analytics(request):
    if request.user.role != 'admin':
        messages.error(request, "Access Denied: You do not have permission to view financial reports.")
        return redirect('dashboard') # This sends them back to their own dashboard

    # 1. Total Revenue (Paid)
    paid_inv = Invoice.objects.filter(payment_status='paid')
    total_revenue = (paid_inv.aggregate(Sum('labour_charge'))['labour_charge__sum'] or 0) + \
    (InvoicePart.objects.filter(invoice__in=paid_inv).aggregate(
        total=Sum(F('quantity_used') * F('part__unit_price'))
    )['total'] or 0)

    # 2. Pending Revenue (Unpaid)
    unpaid_inv = Invoice.objects.filter(payment_status='unpaid')
    pending_revenue = (unpaid_inv.aggregate(Sum('labour_charge'))['labour_charge__sum'] or 0) + \
    (InvoicePart.objects.filter(invoice__in=unpaid_inv).aggregate(
        total=Sum(F('quantity_used') * F('part__unit_price'))
    )['total'] or 0)

    # 3. Monthly Revenue Trend (FIXED NESTING)
    monthly_data_map = defaultdict(float)

    # Sum Labour per month
    labour_by_month = paid_inv.annotate(month=TruncMonth('created_at')).values('month').annotate(m_total=Sum('labour_charge'))
    for entry in labour_by_month:
        month_str = entry['month'].strftime('%b %Y')
        monthly_data_map[month_str] += float(entry['m_total'])

        # Sum Parts per month (This was inside the other loop in your code, fixed now)
        parts_by_month = InvoicePart.objects.filter(invoice__payment_status='paid').annotate(
            month=TruncMonth('invoice__created_at')
        ).values('month').annotate(
            m_total=Sum(F('quantity_used') * F('part__unit_price'))
        )
    for entry in parts_by_month:
        month_str = entry['month'].strftime('%b %Y')
        monthly_data_map[month_str] += float(entry['m_total'])

    # Sort the months correctly for the chart
    sorted_months = sorted(monthly_data_map.keys(), key=lambda x: datetime.strptime(x, '%b %Y'))
    labels = sorted_months
    values = [monthly_data_map[m] for m in sorted_months]

    # 4. Recent Transactions
    recent_invoices = Invoice.objects.order_by('-created_at')[:10]

    context = {
        'total_revenue': total_revenue,
        'pending_revenue': pending_revenue,
        'labels': json.dumps(labels),
        'values': json.dumps(values),
        'recent_invoices': recent_invoices,
    }
    return render(request, 'revenue_analytics.html', context)

