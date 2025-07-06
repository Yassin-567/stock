from django import forms
from .models import CustomUser, Item, Company,Job,Comment,WarehouseItem,JobItem,Engineer,category
from django.contrib.auth.models import Group
from django.forms import HiddenInput
from django.db.models import Q
from django.core.exceptions import ValidationError
from .myfunc import items_arrived,items_not_used


class loginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)

    fields=['email','password']


class companyregisterForm(forms.ModelForm):
    
    class Meta:
        model = Company
        fields = ['company_name','company_email','address','phone',]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Company Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Company Email'}),
        }
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('company_email')
        if email and Company.objects.filter(company_email=email).exists():
            raise ValidationError("A company with this email already exists")
        return cleaned_data
    def __init__(self, *args, user=None, updating=False,enable_edit=False,**kwargs):
            super().__init__(*args, **kwargs)
            if user is not None and updating: 
                if  not enable_edit:
                    for field in self.fields.values():
                        
                        field.widget.attrs['class'] = 'faded-input'
                        field.widget.attrs['disabled'] = 'disabled'

class registerForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        required=True,
        help_text='Enter a secure password'
    )
    
    # Add password confirmation field
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        required=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email']  # Don't include password here
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    def clean_email(self):
        
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists. Please use a different email address.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Only set password if one is provided (for updates)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
    
class registerworker(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        required=True,
        help_text='Enter a secure password'
    )
    
    # Add password confirmation field
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        required=True
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email','permission','is_banned']
        
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'permission': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing = editing
        
    # def clean_email(self):
    #     email = self.cleaned_data.get('email')
    #     if not self.editing:
            
    #         if CustomUser.objects.filter(email=email).exists():
    #             raise ValidationError("A user with this email already exists. Please use a different email address.")
    #         return email
    def clean(self):
        
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data
    
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user




    
class JobForm(forms.ModelForm):
    
    class Meta:
        model = Job
        fields = '__all__'
        exclude = ['user','quotation']
        labels = {
            'name': 'Part Name',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select', 'id': 'id_status'}),
            #'quotation':forms.NumberInput(attrs={'id':'id_quoting_price'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            #'arrived_quantity': forms.NumberInput(attrs={'class': 'form-control', 'id': 'arrived_quantity'}),
            'quoted':forms.HiddenInput(),
            'items_arrived':forms.HiddenInput(),
            'job_id': forms.TextInput(attrs={  # Override widget for job_id
                'type': 'text',  # Set input type to text
                'inputmode': 'numeric',  # Allow numeric input
                'pattern': '[0-9]*',  # Numeric pattern
                'placeholder': 'Enter Job ID',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, updating=False, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.status=='cancelled' or self.instance.status=='completed' :
            for name,field in self.fields.items():
                if name!='status':
                    field.widget.attrs['readonly'] = 'readonly'
                    field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' faded-input'

        self.fields['company'].widget=forms.HiddenInput()
        if updating:
            # Disable fields if updating
            self.fields['job_id'].widget=forms.HiddenInput()
    def clean(self,*args, **kwargs):
        cleaned_data=super().clean()
        status=cleaned_data.get('status')
        items_arrivedd=cleaned_data.get('items_arrived')
        job=self.instance
        
        if job.pk:
            #if self.fields['status']=='quoted':
                
            items_count=job.items.all().count()
            if status=='ready' and  not (items_arrived(job) and items_not_used(job)) and items_count>0 :
            
                raise forms.ValidationError("Not all items arrived")
            elif status=='ready' and job.items.exclude(is_used=False).exists():
                raise forms.ValidationError("There is a used item")
            return cleaned_data
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'content_type', 'object_id']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'content_type': forms.HiddenInput(),
            'object_id': forms.HiddenInput(),
            'company': forms.HiddenInput(),
        }
    

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = '__all__' 
        exclude = ['added_by','company','is_used','is_warehouse_item','warehouse_quantity','is_moved_to_warehouse',]
        labels = {
            'name': 'Part Name',
        }
        widgets = {
            #'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select','id':'status'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            #'arrived_quantity': forms.NumberInput(attrs={'class': 'form-control','id':'arrived_quantity'}),
            'part_number':forms.TextInput(attrs={  # Override widget for job_id
                'type': 'text',  # Set input type to text
                'inputmode': 'numeric',  # Allow numeric input
                #'pattern': '[0-9]*',  # Numeric pattern
                'placeholder': 'Enter part number',
                'class': 'form-control',}),
            'reference':forms.Textarea(attrs={'rows':1}),
        }

    def __init__(self, *args, updating=False,completed=False,job=False, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['job'].empty_label = None
        if updating:
            
            self.fields['part_number'].widget=forms.HiddenInput()
            if completed:
                for field in self.fields.values():
                    field.widget.attrs['class'] = 'faded-input'
                    field.widget.attrs['disabled'] = 'disabled'
        elif job==None:
            self.fields['required_quantity'].widget=forms.HiddenInput()
            self.fields['ordered'].widget=forms.HiddenInput()
    def clean(self,*args, **kwargs):

        cleaned_data = super().clean()
        job_quantity = cleaned_data.get('required_quantity')
        arrived_quantity = cleaned_data.get('arrived_quantity')
        ordered = cleaned_data.get('ordered')
        job=cleaned_data.get('job')

        if job_quantity == arrived_quantity and not ordered and job:
            raise forms.ValidationError("Items can't arrive without ordering")
        elif job_quantity < arrived_quantity and job:
            raise forms.ValidationError("Arrived quantity can't be more than the required quantity")

        return cleaned_data
class JobItemForm(forms.ModelForm):
    class Meta:
        model=JobItem
        fields='__all__'
        exclude=['job','from_warehouse','is_used','status','was_for_job','added_by','notes']
        widgets={'reference':forms.Textarea(attrs={'rows':1}),}
    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].widget=forms.HiddenInput()
        self.fields['job_quantity'].label='Required quantity'
        if self.instance.is_used or self.instance.job.status=='completed' :
            for field in self.fields.values():
                field.widget.attrs['class'] = 'faded-input'
                field.widget.attrs['disabled'] = 'disabled'

        #self.fields['status'].choices=[  (value, label) for value, label in self.fields['status'].choices if value != 'arrived']
        if self.instance.from_warehouse or (self.instance.was_for_job and self.instance.from_warehouse):
            self.fields['arrived_quantity'].widget=forms.HiddenInput()
            self.fields['ordered'].widget=forms.HiddenInput()
           # self.fields['status'].widget=forms.HiddenInput()
        # if item.item.from_warehouse:
        #     self.fields['job_quantity'].widget=forms.HiddenInput()
    def clean(self,*args, **kwargs):
        cleaned_data = super().clean()
        job_quantity = cleaned_data.get('job_quantity')
        arrived_quantity = cleaned_data.get('arrived_quantity')
        ordered = cleaned_data.get('ordered')
        
        if job_quantity == arrived_quantity and not ordered and not self.instance.from_warehouse:
            raise forms.ValidationError("Items can't arrive without ordering")
        elif job_quantity<arrived_quantity and not  self.instance.from_warehouse:
            raise forms.ValidationError("Arrived quantity can't be more than the required quantity")
        elif job_quantity<arrived_quantity and  self.instance.from_warehouse:
            raise forms.ValidationError("Required quantity can't be Zero, you can move instead")
        return cleaned_data
class WarehouseitemForm(forms.ModelForm):
    class Meta:
        model = WarehouseItem
        fields = '__all__' 
        exclude = ['added_by','company','is_used','item','status','is_moved_from_job','was_for_job','is_moved_to_warehouse','is_move_to_warehouse',]
        labels = {
            'name': 'Part Name',
        }
        widgets = {
            #'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select','id':'status'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            #'arrived_quantity': forms.NumberInput(attrs={'class': 'form-control','id':'arrived_quantity'}),
            'part_number':forms.TextInput(attrs={  # Override widget for job_id
                'type': 'text',  # Set input type to text
                'inputmode': 'numeric',  # Allow numeric input
                #'pattern': '[0-9]*',  # Numeric pattern
                'placeholder': 'Enter part number',
                'class': 'form-control',}),
            'reference':forms.Textarea(attrs={'rows':1})
        }
    
    # def __init__(self, *args,warehouse_item, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # self.fields['arrived_quantity'] = forms.IntegerField(
    #     #         initial=warehouse_item.warehouse_quantity if warehouse_item else None,
    #     #         label="Stock Quantity",
    #     #         widget=forms.NumberInput(attrs={'class': 'form-control'}))
       
class EngineerForm(forms.ModelForm):
    class Meta:
        model = Engineer
        fields = '__all__'
        exclude=['company']

class CategoriesForm(forms.ModelForm):
    class Meta:
        model = category
        fields = ['category']
        widgets = {
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
        }
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
class SearchForm(forms.Form):
    search_text = forms.CharField(max_length=100)#-
    status_filter = forms.ChoiceField(choices=['ready','paused','completed','cancelled','quoted'], required=False)     #-
    supplier_filter = forms.CharField(max_length=90, required=False)#-
    min_price_filter = forms.DecimalField(max_digits=10, decimal_places=2, required=False)#-
    max_price_filter = forms.DecimalField(max_digits=10, decimal_places=2, required=False)#-
    min_quantity_filter = forms.IntegerField(required=False)#-
    max_quantity_filter = forms.IntegerField(required=False)#-
