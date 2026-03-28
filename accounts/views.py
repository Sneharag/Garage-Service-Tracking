from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .forms import SignupForm,UserCreateForm
from .models import User

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {
        'error': 'Invalid username or password. Please try again.'
    })
    return render(request, 'login.html')

def user_logout(request):
    logout(request)

    return redirect('home')

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'customer'
            user.save()
            return redirect('login')
        # if form is invalid, fall through and re-render with errors
    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})


def profile(request):
    return render(request, 'profile.html')

@login_required
def add_user(request):

    if request.user.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()
            return redirect('user_list')

    else:
        form = UserCreateForm()

    return render(request, 'add_user.html', {'form': form})

@login_required
def user_list(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    users = User.objects.exclude(role='admin').order_by('-id')

    return render(request, 'user_list.html', {'users': users})        

@login_required
def user_edit(request, pk):
    vehicle = User.objects.get(pk=pk)

    if request.method == 'POST':
        form = UserCreateForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
            form = UserCreateForm(instance=vehicle)

    return render(request, 'add_user.html', {'form': form})

@login_required
def user_delete(request, pk):
    user = User.objects.get(pk=pk)
    user.delete()
    return redirect('user_list')

@login_required
def user_detail(request, id):

    if request.user.role != 'admin':
        return redirect('dashboard')

    user = User.objects.get(id=id)

    return render(request, 'user_detail.html', {'user_obj': user})

def forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return render(request, 'forgot_password.html', {
        'error': 'No account found with that username.'
        })

        # check passwords match
        if new_password != confirm_password:
            return render(request, 'forgot_password.html', {
        'error': 'Passwords do not match.',
        'username': username
        })

        # check password length
        if len(new_password) < 6:
            return render(request, 'forgot_password.html', {
        'error': 'Password must be at least 6 characters.',
        'username': username
        })

        # save new password
        user.set_password(new_password)
        user.save()

        return render(request, 'forgot_password.html', {
        'success': 'Password updated successfully! You can now login.'
        })

    return render(request, 'forgot_password.html')

