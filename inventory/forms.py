from django import forms
from .models import CustomUser, Item, Company,Job,Comment,WarehouseItem,JobItem
from django.contrib.auth.models import Group
from django.forms import HiddenInput
from django.db.models import Q


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
    def __init__(self, *args, user=None, updating=False,**kwargs):
            super().__init__(*args, **kwargs)
            if user is not None and updating: 
                if   not user.company_owner==user or user.company==None:
                    for field in self.fields.values():
                        
                        field.widget.attrs['class'] = 'faded-input'
                        field.widget.attrs['disabled'] = 'disabled'

class registerForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    is_banned=forms.BooleanField( required=False,
    initial=False,
    label="Ban this user", 
    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'groups', 'company']
        widgets = {
            'email': forms.EmailInput(),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'company': forms.HiddenInput(),
            
            #'groups': forms.MultipleHiddenInput(),  
        }

    def __init__(self, *args,registering=False,adding_worker=False, **kwargs):
        super().__init__(*args, **kwargs)

        if registering:
            self.fields['is_banned'].widget = forms.HiddenInput()
            #self.fields['groups'].widget = forms.MultipleHiddenInput()
        if adding_worker:
            self.fields['is_banned'].widget = forms.HiddenInput()
        
    def save(self, commit=True):
        """ Hash the password before saving """
        
        user = super().save(commit=False)
        
        user.set_password(self.cleaned_data["password"])  # Securely hash password
        # user.company=Company.objects.get(id=user.company.id)
        if commit:
            user.save()
            self.save_m2m()  # Save groups if assigned
        return user
    
class JobForm(forms.ModelForm):
    
    class Meta:
        model = Job
        fields = '__all__'
        exclude = ['user', 'company','items_arrived']
        labels = {
            'name': 'Part Name',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select', 'id': 'status'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            #'arrived_quantity': forms.NumberInput(attrs={'class': 'form-control', 'id': 'arrived_quantity'}),
            'quoted':forms.HiddenInput(),
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
        
        if updating:
            # Disable fields if updating
            self.fields['job_id'].widget=forms.HiddenInput()
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
    
''
class StokcItemsForm(forms.ModelForm):
    stock_items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),
        #widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Stock Items",)
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        # instance = kwargs.get('instance')
        # print (kwargs)
        #instance.company if instance else kwargs.get('company', None)
        if company:
            self.fields['stock_items'].queryset = WarehouseItem.objects.filter(
                
                item__company=company,
                
                warehouse_quantity__gt= 0,
            )
    def clean(self):
        cleaned_data = super().clean()
        
        #job_quantity = cleaned_data.get('job_quantity')
        stock_items = cleaned_data.get('stock_items')[0]
        print(stock_items)
        
        
            
        # if job_quantity > stock_items.arrived_quantity:
        #     raise forms.ValidationError(
        #         f"Only {stock_items.arrived_quantity} parts are available in stock."
        #     )

        return cleaned_data


    class Meta:
        model=Item
        fields=['required_quantity']
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = '__all__' 
        exclude = ['added_by','company','is_used','is_warehouse_item','warehouse_quantity','is_moved_to_warehouse','notes','is_move_to_warehouse']
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

    def __init__(self, *args, updating=False,completed=False,job=False, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['job'].empty_label = None
        if updating:
            instance = kwargs.get('instance')
            #company=instance.company
            #self.fields['job'].queryset=Job.objects.filter(company=company)
            self.fields['part_number'].widget=forms.HiddenInput()
            if completed:
                for field in self.fields.values():
                    field.widget.attrs['class'] = 'faded-input'
                    field.widget.attrs['disabled'] = 'disabled'
        elif job==None:
            self.fields['required_quantity'].widget=forms.HiddenInput()
class JobItemForm(forms.ModelForm):
    class Meta:
        model=JobItem
        fields='__all__'
        exclude=['job','from_warehouse']
    # def __init__(self, *args,**kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['job'].widget=forms.HiddenInput()
class SearchForm(forms.Form):
    search_text = forms.CharField(max_length=100)#-
    status_filter = forms.ChoiceField(choices=[('', 'All statuses'), ('a', 'Arrived'), ('c', 'Ordered'), ('d', 'Taken'), ('e', 'Job done'), ('b', '')], required=False)     #-
    supplier_filter = forms.CharField(max_length=90, required=False)#-
    min_price_filter = forms.DecimalField(max_digits=10, decimal_places=2, required=False)#-
    max_price_filter = forms.DecimalField(max_digits=10, decimal_places=2, required=False)#-
    min_quantity_filter = forms.IntegerField(required=False)#-
    max_quantity_filter = forms.IntegerField(required=False)#-
