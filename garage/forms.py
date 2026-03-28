from django import forms
from .models import Vehicle,ServiceJob,Part,Invoice,InvoicePart
from accounts.models import User

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['customer'].queryset = User.objects.filter(role='customer')

class ServiceJobForm(forms.ModelForm):

    class Meta:
        model = ServiceJob
        fields = ['mechanic', 'problem_description']
        widgets = {
    'mechanic': forms.Select(attrs={'class': 'form-select'}),
    'problem_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 FILTER CUSTOMER
        # self.fields['customer'].queryset = User.objects.filter(role='customer')

        # 🔧 Only mechanics
        self.fields['mechanic'].queryset = User.objects.filter(role='mechanic')

        # 🚗 All vehicles
        # self.fields['vehicle'].queryset = Vehicle.objects.all()

class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ['name', 'description', 'quantity', 'unit_price', 'low_stock_threshold']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['labour_charge', 'payment_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class InvoicePartForm(forms.ModelForm):
    class Meta:
        model = InvoicePart
        fields = ['part', 'quantity_used']

