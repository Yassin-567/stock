from django import forms
from django.contrib.auth.models import Group


class FormHandler:
    def __init__(self, form, user, target_user):
        self.form = form
        self.user = user
        self.target_user = target_user

        self.is_owner = hasattr(user, 'company') and user.company and user.company.owner == user
        self.is_admin = user.groups.filter(name="Admin").exists()
        self.is_employee = user.groups.filter(name="Employee").exists()
        self.is_self = user == target_user

    def set_form_fields(self):
        if self.is_owner and self.is_self:
            self.form.fields['groups'].widget = forms.MultipleHiddenInput()
            self.form.fields['is_banned'].widget=forms.HiddenInput()
        elif self.is_owner:
            self.form.fields['groups'].widget = forms.Select()
            self.form.fields['groups'].queryset = Group.objects.all().exclude(name='Ban')

        elif self.is_admin and self.is_self:
            self.form.fields['groups'].widget = forms.MultipleHiddenInput()
            self.form.fields['is_banned'].widget=forms.HiddenInput()
        elif self.is_admin:
            self.form.fields['groups'].widget = forms.Select()
            self.form.fields['groups'].queryset = Group.objects.filter(name__in=["Admin", "Employee"])

        elif self.is_employee:
            self.form.fields['groups'].widget = forms.MultipleHiddenInput()
            self.form.fields['is_banned'].widget=forms.HiddenInput()
    def get_user_group(self):
        # Handle is_banned if present in form
        if self.form.cleaned_data.get("is_banned"):
            return [Group.objects.get(name='Ban')]

        if self.is_owner and self.is_self:
            return [Group.objects.get(name='Admin')]

        elif self.is_owner or self.is_admin:
            # groups can be a queryset or a single selection
            selected = self.form.cleaned_data['groups']
            return selected if isinstance(selected, list) else [selected]

        elif self.is_admin and self.is_self:
            return [Group.objects.get(name='Admin')]

        elif self.is_employee:
            return [Group.objects.get(name='Employee')]

        return []  # fallback
