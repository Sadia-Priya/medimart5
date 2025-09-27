"""
Forms used throughout the pharmacy application.
Includes a registration form for new users and a form for uploading prescriptions.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Prescription, Appointment


class SignupForm(UserCreationForm):
    """
    User registration form extending the built-in UserCreationForm.
    Adds an email field with validation.
    """
    email = forms.EmailField(
        required=True,
        help_text='Required. Enter a valid email address.'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class PrescriptionForm(forms.ModelForm):
    """
    Form to upload a prescription image.
    """
    class Meta:
        model = Prescription
        fields = ['image']


# forms.py
class AppointmentPrescriptionForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['prescription_file']
        widgets = {
            'prescription_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

from django import forms
from .models import eLabSchedule

from django import forms
from .models import eLabSchedule

class eLabScheduleForm(forms.ModelForm):
    AVAILABLE_TESTS = {
        'Complete Blood Count (CBC)': ('Blood', 500),
        'Lipid Profile': ('Blood', 1200),
        'Blood Sugar': ('Blood', 400),
        'Urine Analysis': ('Urine', 300),
        'Liver Function Test': ('Pathology', 1500),
        'Kidney Function Test': ('Pathology', 1300),
        'Thyroid Profile': ('Pathology', 1800),
    }

    test_name = forms.ChoiceField(choices=[], required=True, label='Test Name')
    test_price = forms.DecimalField(
        max_digits=8, decimal_places=2, required=True, widget=forms.NumberInput(attrs={'readonly':'readonly'})
    )

    class Meta:
        model = eLabSchedule
        fields = ['test_type', 'test_name', 'test_price', 'preferred_date', 'preferred_time', 'address', 'phone']
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type':'date'}),
            'preferred_time': forms.TimeInput(attrs={'type':'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['test_name'].choices = [(name, f"{name} – ৳{price}") for name, (typ, price) in self.AVAILABLE_TESTS.items()]

        if self.instance and self.instance.test_name:
            info = self.AVAILABLE_TESTS.get(self.instance.test_name)
            if info:
                self.fields['test_type'].initial = info[0]
                self.fields['test_price'].initial = info[1]

    def clean(self):
        cleaned_data = super().clean()
        test_name = cleaned_data.get('test_name')
        if test_name in self.AVAILABLE_TESTS:
            test_type, test_price = self.AVAILABLE_TESTS[test_name]
            cleaned_data['test_type'] = test_type
            cleaned_data['test_price'] = test_price
        return cleaned_data

class eLabPaymentForm(forms.ModelForm):
    class Meta:
        model = eLabSchedule
        fields = ['payment_method', 'transaction_id']
        widgets = {
            'transaction_id': forms.TextInput(attrs={'placeholder':'Enter Transaction ID'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('payment_method')
        txn = cleaned_data.get('transaction_id')

        if method and not txn:
            raise forms.ValidationError("Transaction ID is required for payment.")
        return cleaned_data



class eLabReportUploadForm(forms.ModelForm):
    class Meta:
        model = eLabSchedule
        fields = ['report_file', 'report_verified']
        widgets = {
            'report_verified': forms.CheckboxInput(attrs={'style':'transform:scale(1.2);'}),
        }

