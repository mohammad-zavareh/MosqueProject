from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

_INPUT = {"class": "form-ctrl"}


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={
            **_INPUT,
            "placeholder": "رمز عبور",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=forms.PasswordInput(attrs={
            **_INPUT,
            "placeholder": "تکرار رمز عبور",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model  = User
        fields = ["username", "first_name", "last_name"]
        widgets = {
            "username":   forms.TextInput(attrs={
                              **_INPUT,
                              "placeholder": "نام کاربری",
                              "autocomplete": "username",
                          }),
            "first_name": forms.TextInput(attrs={
                              **_INPUT,
                              "placeholder": "نام",
                          }),
            "last_name":  forms.TextInput(attrs={
                              **_INPUT,
                              "placeholder": "نام خانوادگی",
                          }),
        }
        labels = {
            "username":   "نام کاربری",
            "first_name": "نام",
            "last_name":  "نام خانوادگی",
        }
        error_messages = {
            "username": {
                "required": "نام کاربری الزامی است.",
                "unique":   "این نام کاربری قبلاً ثبت شده است.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = False
        self.fields["last_name"].required  = False

    def clean_password1(self):
        pw = self.cleaned_data.get("password1")
        if pw:
            validate_password(pw)
        return pw

    def clean_password2(self):
        pw1 = self.cleaned_data.get("password1")
        pw2 = self.cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        return pw2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user



class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="رمز عبور فعلی",
        widget=forms.PasswordInput(attrs={
            **_INPUT,
            "placeholder": "رمز عبور فعلی خود را وارد کنید",
            "autocomplete": "current-password",
        }),
        error_messages={"required": "وارد کردن رمز عبور فعلی الزامی است."},
    )
    new_password1 = forms.CharField(
        label="رمز عبور جدید",
        widget=forms.PasswordInput(attrs={
            **_INPUT,
            "placeholder": "رمز عبور جدید",
            "autocomplete": "new-password",
        }),
        error_messages={"required": "وارد کردن رمز عبور جدید الزامی است."},
    )
    new_password2 = forms.CharField(
        label="تکرار رمز عبور جدید",
        widget=forms.PasswordInput(attrs={
            **_INPUT,
            "placeholder": "تکرار رمز عبور جدید",
            "autocomplete": "new-password",
        }),
        error_messages={"required": "تکرار رمز عبور جدید الزامی است."},
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if old_password and not self.user.check_password(old_password):
            raise forms.ValidationError("رمز عبور فعلی صحیح نیست.")
        return old_password

    def clean_new_password1(self):
        pw = self.cleaned_data.get("new_password1")
        if pw:
            validate_password(pw, self.user)
        return pw

    def clean_new_password2(self):
        pw1 = self.cleaned_data.get("new_password1")
        pw2 = self.cleaned_data.get("new_password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("رمز عبور جدید و تکرار آن یکسان نیستند.")
        return pw2

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data["new_password1"])
        if commit:
            self.user.save()
        return self.user