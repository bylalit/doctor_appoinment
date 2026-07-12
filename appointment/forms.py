from django import forms
from .models import Category

class SpecialityForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']  # Kyunki description nahi chahiye, sirf name field add ki hai
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3 p-3',
                'placeholder': 'Enter speciality name (e.g., Cardiology, Pediatrics)',
                'style': 'border: 1px solid #ced4da; font-size: 16px;'
            }),
        }
        
