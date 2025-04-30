from django import forms
from django.contrib.auth.models import Group


class FormHandler:
    def __init__(self, form, user, target_user,show_choices=False):
        self.form = form
        self.user = user
        self.target_user = target_user
        self.show_choices=show_choices
        self.is_owner = hasattr(user, 'company') and user.company and user.company.owner == user
        self.is_admin = user.groups.filter(name="Admin").exists()
        self.is_employee = user.groups.filter(name="Employee").exists()
        self.is_self = user == target_user

    def set_form_fields(self):
        
        if self.target_user.groups.filter(name="Ban").exists():
            
            self.form.fields['is_banned'].initial=True
        if self.show_choices and self.is_owner and self.is_self:
            print("1")
            self.form.fields['groups'].widget = forms.MultipleHiddenInput()
            self.form.fields['is_banned'].widget=forms.HiddenInput()
        elif self.show_choices and self.is_owner:
            print("2")
            self.form.fields['groups'].widget = forms.Select()
            self.form.fields['groups'].queryset = Group.objects.all().exclude(name='Ban')
        elif self.show_choices :
            print("3")
            self.form.fields['groups'].queryset = Group.objects.all().exclude(name='Ban')
        else:
            print("4")
            self.form.fields['groups'].widget = forms.MultipleHiddenInput()
            self.form.fields['is_banned'].widget=forms.HiddenInput()

    def get_user_group(self):
        # Handle is_banned if present in form
        if self.form.cleaned_data.get("is_banned"):
            print("User is banned")
            return Group.objects.get(name='Ban')
            
        if self.is_owner and self.is_self:
            print("Owner is self")
            return Group.objects.get(name='Admin')

        elif self.is_owner or self.is_admin:
            # groups can be a queryset or a single selection
            selected = self.form.cleaned_data['groups']
            print("Selected groups:", selected[0])
            return Group.objects.get(name=selected[0])










    # def set_form_fieldss(self):
    #     if self.is_owner and self.is_self:
    #         print("1")
    #         self.form.fields['groups'].widget = forms.MultipleHiddenInput()
    #         self.form.fields['is_banned'].widget=forms.HiddenInput()

    #     elif self.is_owner:
    #         print("2")
    #         self.form.fields['groups'].widget = forms.Select()
    #         self.form.fields['groups'].queryset = Group.objects.all().exclude(name='Ban')

    #     elif self.is_admin and self.is_self:
    #         print("3")
    #         self.form.fields['groups'].widget = forms.MultipleHiddenInput()
    #         self.form.fields['is_banned'].widget=forms.HiddenInput()

    #     elif self.is_admin and (self.target_user == self.user.company.owner or self.target_user.groups.filter(name="Admin").exists()):
    #         print("4")
    #         self.form.fields['groups'].widget = forms.MultipleHiddenInput()
    #         self.form.fields['is_banned'].widget=forms.HiddenInput()

    #     elif self.is_admin:
    #         print("5")
    #         self.form.fields['groups'].widget = forms.Select()
    #         self.form.fields['groups'].queryset = Group.objects.filter(name__in=["Admin", "Employee"])

    #     elif self.is_employee:
    #         print("6")
    #         self.form.fields['groups'].widget = forms.MultipleHiddenInput()
    #         self.form.fields['is_banned'].widget=forms.HiddenInput()
    # def get_user_groupp(self):
    #     # Handle is_banned if present in form
    #     if self.form.cleaned_data.get("is_banned"):
            
    #         print("User is banned")
    #         return Group.objects.get(name='Ban')
            
    #     if self.is_owner and self.is_self:
    #         print("Owner is self")
    #         return Group.objects.get(name='Admin')

    #     elif self.is_owner or self.is_admin:
    #         # groups can be a queryset or a single selection
    #         selected = self.form.cleaned_data['groups']
    #         print("Selected groups:", selected[0])
    #         return Group.objects.get(name=selected[0]) #if isinstance(selected, list) else [selected]

    #     elif self.is_admin and self.is_self:
    #         print("Admin is self")
    #         return Group.objects.get(name='Admin')

    #     elif self.is_employee:
    #         print("Employee is self")
    #         return Group.objects.get(name='Employee')

    #     return []  # fallback

class WareohuseFormHandler:
    def __init__(self, form,):
        self.form = form
    def set_form_fields(self):
        #self.form.fields['job'].widget=forms.HiddenInput()
        self.form.fields['job_quantity'].widget=forms.HiddenInput()
        self.form.fields['arrived_quantity'].label="Stock Quantity"

def calculate_item(item,job_qunatity):
    quantity=item.arrived_quantity
    item.arrived_quantity=quantity-job_qunatity
    item.save()