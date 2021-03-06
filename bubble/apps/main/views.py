from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.contrib import messages
from django.conf import settings
import stripe
import bcrypt
from datetime import date
from models import *

from datetime import datetime

## BUBLE MAIN  VIEWS ##
def index(request):
    if 'user_id' in request.session:
        return redirect('/dashboard')
    return render(request, 'main/index.html')

def login(request):
    try:
        user = User.objects.get(email = request.POST['email'])
        if bcrypt.checkpw(request.POST['password'].encode(), user.password.encode()):
            request.session['user_id'] = user.id
            # get name of user
            name = User.objects.get(id = user.id)
            #get level of user
            admin_check = name.level
            #admin redirect
            if admin_check == 1:
                #test for redirectreturn redirect ('/order')
                request.session['name'] = name.name
                return redirect('/dashboard')
            elif admin_check == 0:
                request.session['name'] = name.name
                return redirect('/dashboard')
    except:
        messages.error(
        request, "Email/Password combination FAILED")
        return redirect('/')

def register(request):

    errors_register = []

    if len(request.POST['name']) < 1:
        errors_register.append("Name must be at least two characters.")
    if len(request.POST['email']) < 3:
        errors_register.append("Email must be at least four characters.")
    if len(request.POST['street']) < 3:
        errors_register.append("Street Address must be at least four characters.")
    if len(request.POST['city']) < 2:
        errors_register.append("City must be at least three characters.")
    if len(request.POST['state']) <= 1:
        errors_register.append("Please enter a state.")
    if len(request.POST['zip']) < 4:
        errors_register.append("Please enter a valid zip code.")
    if len(request.POST['password']) < 7:
        errors_register.append("Password must be at least eight characters.")
    if request.POST['password'] != request.POST['confirm_password']:
        errors_register.append("Password and password confirmation don't match.")

    if errors_register:
        for err in errors_register:
            messages.error(request, err)
        return redirect('/')
    else:
        try:
            User.objects.get(email=request.POST['email'])
            messages.error(request, "User with that email already exists.")
            return redirect('/')
        except User.DoesNotExist:
            password=request.POST['password']
            ## Hasing the password
            safe_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

            name = request.POST['name']
            email = request.POST['email']
            phone_number = request.POST['phone_number']
            street = request.POST['street']
            city = request.POST['city']
            state = request.POST['state']
            zip = request.POST['zip']
            # Create Record
            # Level = 0 (Normal User)
            # Level = 1 (Admin)
            address = Address.objects.create(street=street, city=city, state=state, zip=zip)
            User.objects.create(name=name, email=email, phone_number = phone_number,  password=safe_password, address=address, level="0")
            #create session to redirect to dashboard for NORMAL USERS
            user_register = User.objects.get(email=email)
            request.session['user_id'] = user_register.id
            request.session['name'] = user_register.name
            return redirect('/dashboard')

def logout(request):
    request.session.clear()
    return redirect ('/')

############# HOME PAGE ##################
def dashboard(request):
    if not 'user_id' in request.session:
        return redirect('/')

    if request.method == "GET":
        user = User.objects.get(id=request.session['user_id'])

        my_orders = Order.objects.filter(
            customer=user).order_by('-created_at').prefetch_related("list_items", "list_items__product")

        my_orders_items = Product.objects.filter(order=my_orders)

        get_info_update = User.objects.all().select_related("address").get(id=request.session['user_id'])
        context = {
            'user': user,
            'my_orders': my_orders,
            'my_orders_items': my_orders_items,
            'info': get_info_update,
        }

        return render(request, 'main/dashboard.html', context)

    if request.method == "POST":
        update_user = User.objects.get(id=request.session['user_id'])
        update_address = Address.objects.get(user=update_user)
        update_user.name = request.POST['name']
        update_user.email = request.POST['email']
        update_user.phone_number = request.POST['phone_number']
        update_address.street = request.POST['street']
        update_address.city = request.POST['city']
        update_address.state = request.POST['state']
        update_address.zip = request.POST['zip']
        update_user.save()
        update_address.save()
        return redirect('/dashboard')


############# ORDER ITEMS ##################
def order(request):
    if not 'user_id' in request.session:
        return redirect('/')

    return render(request, 'main/order.html')
def add_order(request):
    shirt_quant = request.POST['shirt_quant']
    jacket_quant = request.POST['jacket_quant']
    pants_quant = request.POST['pants_quant']
    suit_quant = request.POST['suit_quant']
    coat_quant = request.POST['coat_quant']
    special = request.POST['special']
    method = request.POST['method']
    method_date = datetime.strptime(request.POST['method_date'], '%Y-%m-%d').date()
    total = float(request.POST['total'])
    user = User.objects.get(id=request.session['user_id'])
    order = Order.objects.create(special=special, method=method, method_date=method_date, customer=user, total = total)
    if shirt_quant > 0:
        ListItems.objects.create(order=order, product=Product.objects.get(id=1), quantity=shirt_quant)
    if jacket_quant > 0:
        ListItems.objects.create(
        order=order, product=Product.objects.get(id=2), quantity=jacket_quant)
    if pants_quant > 0:
        ListItems.objects.create(
        order=order, product=Product.objects.get(id=3), quantity=pants_quant)
    if suit_quant > 0:
        ListItems.objects.create(
        order=order, product=Product.objects.get(id=4), quantity=suit_quant)
    if coat_quant > 0:
        ListItems.objects.create(
        order=order, product=Product.objects.get(id=5), quantity=coat_quant)
    return redirect('/dashboard')

###############################
def dev(request):
    return render(request, 'main/dev.html')

def text(request):
    if 'cancel' in request.POST:
        return redirect('/')

    order_id_status2 = request.POST['order_id_status']
    update_status = Order.objects.get(id=order_id_status2)
    update_status.status="Closed"
    update_status.save()
    return redirect('/admin')

def payment(request):
    context = { "stripe_key": settings.STRIPE_PUBLIC_KEY }
    return render(request, "main/payment.html", context)

def checkout(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if request.method == "POST":
        token    = request.POST.get("stripeToken")

        charge  = stripe.Charge.create(
            amount      = 3000,
            currency    = "usd",
        )
        return redirect('/dashboard')

    else:
        return redirect('/dashboard')

def admin(request):
    if User.objects.get(id=request.session['user_id']).level == 0:
        return redirect('/dashboard')
    orders = Order.objects.filter(status='New').select_related("customer").order_by('-created_at')

    sales = Order.objects.aggregate(Sum('total'))
    torders = Order.objects.aggregate(Count('id'))
    context={
        'orders': orders,
        'sales': sales,
        'torders': torders
    }
    return render(request, 'main/admin.html', context)

def orderinfo(request, id):
    if User.objects.get(id=request.session['user_id']).level == 0:
        return redirect('/dashboard')
    order = Order.objects.all().prefetch_related(
    "list_items", "list_items__product").select_related("customer").get(id=id)
    user = User.objects.get(orders=order)
    user_order = User.objects.all().select_related("address").prefetch_related("orders").get(id=user.id)
    user_ordert = Order.objects.filter(customer=user_order).aggregate(Sum('total'))
    user_address = Address.objects.get(user=user)
    user_street = Address.objects.get(user=user).street
    user_streetlist = user_street.split()
    #street =
    context = {
        'order': order,
        'user': user,
        'user_order': user_order,
        'user_ordert': user_ordert,
        'user_address': user_address,
        'user_streetlist': user_streetlist,
    }
    return render(request, 'main/orderinfo.html', context)
