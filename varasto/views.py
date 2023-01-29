# from asyncio.windows_events import NULL
import operator
import re
from django.forms import inlineformset_factory, modelformset_factory
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
    HttpRequest,
    QueryDict
)
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
import pytz
from .forms import CustomUserForm, GoodsForm, Staff_auditForm
from .checkUser import *
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from datetime import datetime, timedelta
from .models import User, Goods, Storage_name, Storage_place, Rental_event, Staff_audit, CustomUser, Settings, Units
from django.db.models import Count
from django.contrib.auth.models import Group

from django.db.models import Min, Max
from .test_views import test

from .anna__views import report, new_event_goods, product_report, inventory, new_user, storage_settings

from .capture_picture import VideoCamera
from django.db.models import Q
# from .alerts import email_alert
from .storage_settings import *
from .services import _save_image
from .services import *

import PIL.Image as Image

from django.middleware.csrf import get_token
from django.conf import settings
from decimal import *
from django.core.serializers import serialize
import json




@login_required()
@user_passes_test(lambda user: user.has_perm("varasto.view_customuser"))
def grant_permissions(request):
    users = CustomUser.objects.all().order_by("id")
    if request.user.is_superuser:
        pass
    elif request.user.role=="management":
        users = users.exclude(is_superuser=True)
    elif request.user.role=="storage_employee":
        users = users.exclude(is_superuser=True).exclude(role="management")
    else:
        users = {}

    paginator = Paginator(users, 10) # Siirtää muuttujan asetukseen
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "users": page_obj
    }

    return render(request, 'varasto/grant_permissions.html', context)

@login_required()
@user_passes_test(lambda user: user.has_perm("varasto.change_customuser"))
def save_permision(request, idx):
    user = CustomUser.objects.get(id=idx)
    user.role = (request.POST.get('roles'))
    print(user.role)
    if request.POST.get('roles') == 'student_extended' or request.POST.get('roles') == 'storage_employee' or request.POST.get('roles') == 'management':
        user.is_staff = True
    elif request.POST.get('roles') == 'super':
        user.is_staff = True
        user.is_superuser = True
    else:
        user.is_staff = False
        user.is_superuser = False
    user.save()

    page_number = request.POST.get('page')

    # return redirect('grant_permissions', page=page_number)
    return redirect(f'/grant_permissions?page={page_number}')



# FUNC inventaario_side_window
def inventaario_side_window(request):
    return render(request, 'varasto/inventaario_side_window.html')


# FUNC person_view
def person_view(request):
    return render(request, 'varasto/person.html')


# FUNC renter
@login_required()
# @user_passes_test(is_not_student, redirect_field_name=None)
@user_passes_test(lambda user: user.has_perm('varasto.view_customuser'))
def renter(request, idx):
    error = {}
    if request.method == 'POST':
        # print(request.POST.get('rental_close'), request.POST.getlist('set_end_date'))
        # print('search_form: ', request.POST.get('rental_event_id')) # Get rental_event id from hidden Input (renter.html)
        # print("BUTTON", request.POST.get('_close_rent_cons'))
        item = Rental_event.objects.get(id=request.POST.get('rental_event_id'))
        product = Goods.objects.get(id=item.item_id)

        if request.POST.get('rental_close'): # UPDATE DATE
            print('RENTAL CLOSE')
            sended_date = request.POST.get('rental_close') 
            date_formated = datetime.strptime(sended_date, '%Y-%m-%d') # Make format stringed date to datetime format
            date_localized = pytz.utc.localize(date_formated) # Add localize into datetime date
            # print(item.item.item_name, date_localized)
            item.estimated_date = date_localized # Save new estimated date into database
            item.save()

        def return_products(got_amount):
            if item.amount and (item.amount - got_amount) >= 0 and isinstance(got_amount, int):
                product.amount = product.amount + got_amount
            elif item.contents and (item.contents - got_amount) >= 0:
                product.amount_x_contents = product.amount_x_contents + got_amount
            else:
                return False
            item.returned = got_amount
            return True

        def update_amount_data():
            if request.POST.getlist('everything_returned'):
                got_amount = item.amount if item.amount else item.contents 
                if not return_products(got_amount):
                    return False
            if not request.POST.getlist('everything_returned') and request.POST.getlist('return_amount'+str(item.id)):
                got_amount = Decimal(request.POST.get('return_amount'+str(item.id))) if item.contents else int(request.POST.get('return_amount'+str(item.id)))
                return_products(got_amount)
            return True

        if request.POST.getlist('_close_rent_cons'):
            # FIXED inaccuracy of decimal numbers in bootstrap-input-spinner https://www.codingem.com/javascript-how-to-limit-decimal-places/
            print('_close_rent_cons', request.POST.get('return_amount'+str(item.id)))         
            if not item.returned_date: # Need to prevent form resubmission
                if update_amount_data():
                    now = datetime.now()
                    datenow = pytz.utc.localize(now)
                    item.returned_date = datenow # Save new estimated date into database
                    item.save()
                    product.save()
                    return redirect('renter', idx=item.renter_id)
                else:
                    error[0] = "Tapahtuman päivitys epäonnistui, yritä uudelleen"
                    return redirect('renter', idx=item.renter_id)

        if request.POST.getlist('set_end_date'): # CLOSE RENT
            print('set_end_date')
            item.returned = 1
            now = datetime.now()
            datenow = pytz.utc.localize(now)
            item.returned_date = datenow # Save new estimated date into database
            item.save()
        if request.POST.getlist('set_problem'):
            print('PROBLEM')
            item.remarks = request.POST.get('remarks')
            item.save()
        if request.POST.getlist('send_email_to_teacher'):
            subject = "Automaattinen muistutus!"
            text = f"henkilöllä {item.renter.first_name} {item.renter.last_name} on erääntynyt laina: <br>"
            body = f" Tuotteen koodi: {item.item.id} <br> Tuotteen nimi: {item.item.item_name} {item.item.brand} <br> Tuotteen malli: {item.item.model} {item.item.item_type} <br> Tuotteen parametrit: {item.item.size} {item.item.parameters}"
            # to = item.renter.responsible_teacher.email
            # print(subject, text + body, to)
            email_alert(subject, text + body, 'tino.cederholm@gmail.com')
        if request.POST.getlist('send_email_item_is_damaged'):
            subject = "Automaattinen muistutus!"
            text = f"henkilö {item.renter.first_name} {item.renter.last_name} on paluttanut varioittuneen tuotteen: <br>"
            body = f" Tuotteen koodi: {item.item.id} <br> Tuotteen nimi: {item.item.item_name} {item.item.brand} <br> Tuotteen malli: {item.item.model} {item.item.item_type} <br> Tuotteen parametrit: {item.item.size} {item.item.parameters}<br>"
            remarks = f"Vaurion kuvaus: <br> {request.POST.get('damaged_remarks')}"
            # to = item.renter.responsible_teacher.email
            print(subject, text + body + remarks)
            email_alert(subject, text + body + remarks, 'tino.cederholm@gmail.com')

    selected_user = CustomUser.objects.get(id=idx)

    storage_filter = storage_f(request.user)
    rental_events = Rental_event.objects.filter(renter__id=idx).filter(**storage_filter).order_by('-start_date')

    is_staff_user_has_permission_to_edit = request.user.has_perm('varasto.change_rental_event')

    paginator = Paginator(rental_events, 10) # Siirtää muuttujan asetukseen
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'rental_events': page_obj,
        'selected_user': selected_user,
        'idx': idx,
        'is_staff_user_has_permission_to_edit': is_staff_user_has_permission_to_edit,
    }
    return render(request, 'varasto/renter.html', context)


# FUNC new_event
@login_required()
@user_passes_test(lambda user: user.has_perm('varasto.add_rental_event'))
def new_event(request):
    error = {}
    context = {}
    now = datetime.now()
    datenow = pytz.utc.localize(now)

    feedback_status = True
    estimated_date = None
    estimated_date_issmall = False
    changed_user = None
    changed_items = []
    
    r = re.compile("add_item") # html:ssa Inputit näyttävät kuin add_item<count number>, siksi pitää löytää kaikki
    add_items = list(filter(r.match, request.GET)) # Etsimme request.GET:ssa kaikki avaimet, joissa nimella on merkkijono "add_item"

    staff = CustomUser.objects.get(id=request.user.id)
    storage_id = staff.storage_id

    # print('add_items ', add_items)

    r = re.compile("inp_amount") # html:ssa Inputit näyttävät kuin add_item<count number>, siksi pitää löytää kaikki
    inp_amounts = list(filter(r.match, request.GET)) # Etsimme request.GET:ssa kaikki avaimet, joissa nimella on merkkijono "add_item"
    # print(inp_amounts)

    if '_add_user' or '_add_item' in request.GET: # Tarkistetaan, painettiin nappit vai ei
        if request.GET.get('add_user'): # jos user code on kirjoitettiin
            # print('add_user: ', request.GET.get('add_user'))
            try:
                 # saadan user, jolla on sama storage id kuin staffilla. Jos storage_id on NULL niin ei tarkistetaan storage_id (Adminilla ei ole storage_id)
                changed_user = CustomUser.objects.get(code=request.GET.get('add_user')) # FIXED we can add all people from database
                # changed_user = CustomUser.objects.get(Q(code=request.GET.get('add_user')) & Q(storage_id=storage_id)) if storage_id else CustomUser.objects.get(code=request.GET.get('add_user'))
            except:
                error[1] = "Lainaaja ei löydetty"
        if add_items: # jos item codes kirjoitetiin
            for add_item in add_items:
                # print(add_item, ' ', request.GET.get(add_item))
                try:
                    # Jos storage_id on NULL niin etsitaan tavaraa koko tietokannassa (Adminilla ei ole storage_id)
                    new_item = Goods.objects.get(Q(id=request.GET.get(add_item)) & Q(storage_id=storage_id)) if storage_id else Goods.objects.get(id=request.GET.get(add_item))
                    # if new_item.rentable_at: print(new_item, ' rented')
                    if new_item not in changed_items and new_item.is_possible_to_rent[0] == True: # Onko lisättävä tavara jo lisätty and item not consumable
                        changed_items.append(new_item) # Lisätään jos ei 
                    # changed_items.append(Goods.objects.get(Q(id=request.GET.get(add_item)) & Q(storage_id=storage_id))) # saadan kaikki Iteemit changed_items muuttujaan (iteemilla on sama storage id kuin staffilla)
                except:
                    error[2] = "Tavaraa ei löydetty"
        if request.GET.get('estimated_date'):
            get_estimated_date = request.GET.get('estimated_date')
            date_formated = datetime.strptime(get_estimated_date, '%Y-%m-%d') # Make format stringed date to datetime format
            estimated_date = pytz.utc.localize(date_formated) # Add localize into datetime date
            if estimated_date <= datenow: # jos eilinen päivä on valittu kentällä, palautetaan virhe
                estimated_date_issmall = True

    if '_remove_user' in request.GET: # jos _remove_user nappi painettu, poistetaan changed_user sisällöt
        changed_user = None

    if '_remove_item' in request.GET: # jos _remove_item nappi painettu, poistetaan item counter mukaan
        changed_items.pop(int(request.GET.get('_remove_item')))


    def contains(list, filter):
        # print(list, filter)
        for count, x in enumerate(list):
            if x.id == int(filter):
                return count
        return -1
    
    # FIXED Fix float number problem 4.7989999999999995 // FIXED IN bootstrap-input-spinner.js LIBRARY
    # TODO Если в список уже добавлен один расходный материал, то при добавлении в список нового материала обновляется и поля старого, без кнопки фиксации. Надо исправить, чтобы кнопки разных товаров в списке не влияли друг на друга. На перспективу
    r = re.compile("radioUnit") # Define group of variable from Get query
    inp_fixes = list(filter(r.match, request.GET)) # Put all radioUnit### variables into list, ### - item id
    print('radioUnit', inp_fixes)
    if inp_fixes:
        for inp_fix in inp_fixes: # Go through all list
            idx_inp_fix = re.sub(r, '', inp_fix) # Get from the name id 
            # fix_item = '_fix_item'+str(idx_inp_fix)
            # print('fix_item', fix_item)
            idxf = contains(changed_items, idx_inp_fix) # compare lists, find the index of the change_item list
            print('idxf', idxf)

            if idxf != -1:
                changed_items[idxf].radioUnit = request.GET.get(inp_fix) # Set radioUnit value 1 or 0 (first or second radio button)
                changed_items[idxf].item_amount = request.GET.get('inp_amount'+idx_inp_fix) # Set item_amount value 
                changed_items[idxf].fix_item = request.GET.get('_fix_item'+idx_inp_fix) if request.GET.get('_fix_item'+idx_inp_fix) else 1 # Set a fix_item (btn) value: 0, 1. If got none set 1.

            # print('inp_fix', inp_fix)
            # print('idx_inp_fix', idx_inp_fix)

            # print('GET _fix_item'+idx_inp_fix, request.GET.get('_fix_item'+idx_inp_fix)) 

            # print('idxf', idxf)
            # print('radioUnit', request.GET.get(inp_fix))
            # print('item_amount', request.GET.get('inp_amount'+idx_inp_fix))
            # print(changed_items[idxf].id, changed_items[idxf].item_name, changed_items[idxf].item_amount)
    else:
        error[3] = 'Mitään ei löytynyt'



    def serch_fix_item(idx, inp_fixes):
        for inp_fix in inp_fixes:
            # print('inp_fix ', request.GET.get(inp_fix))
            # print('idx ', idx)
            if idx == int(request.GET.get(inp_fix)):
                return True

    if request.method == 'POST': # Jos painettiin Talenna nappi
        if changed_user and changed_items and estimated_date: # tarkistetaan että kaikki kentät oli täytetty
            try:
                renter = CustomUser.objects.get(id=changed_user.id) # etsitaan kirjoitettu vuokraja
                staff = CustomUser.objects.get(id=request.user.id) # etsitaan varastotyöntekija, joka antoi tavara vuokrajalle
            except:
                error[5] = 'Error: Lainaaja ei löydy'
            items = Goods.objects.filter(pk__in=[x.id for x in changed_items]) # etsitaan ja otetaan kaikki tavarat, joilla pk on sama kuin changed_items sisällä
            
            for item in items: # Iteroidaan ja laitetaan kaikki tavarat ja niiden vuokraja Rental_event tauluun
                kwargs = { # Tehdään sanakirja, jossa kaikki kulutusmateriaalien ja työkalujen kentät ovat samat
                    'item': item, 
                    'renter': renter, 
                    'staff': staff,
                    'start_date': datenow,
                    'storage_id': staff.storage_id,
                    'estimated_date': estimated_date,
                    'amount': 1,
                    # 'units': item.unit if not unit else None
                }
                if item.cat_name_id == CATEGORY_CONSUMABLES_ID:  # Jos se on kulutusmateriaali
                    unit = int(request.GET.get('radioUnit'+str(item.id))) # Saadaan yksikköä 1 on pakkaus kpl, 0 on sisällön määrää
                    item_amount = Decimal(request.GET.get('inp_amount'+str(item.id))) # Saadaan tavaran määrä
                    print('GET unit', str(item.id), unit)
                    print('GET item_amount', str(item.id), item_amount)
                    if (item_amount <= int(item.amount)) or (item_amount <= item.amount_x_contents): # Tarkistus, onko varastossa tarpeeksi tuotteita?
                        try:
                            if unit: # Jos yksikkö on pakkaus, kpl
                                item.amount = int(item.amount) - item_amount
                                kwargs['amount'] = item_amount
                                print('item.amount', item.amount)
                            else: # Jos yksikkö on sisällön määrää
                                # amount_x_contents = item.amount * item.contents # formula
                                print('item.amount_x_contents', item.amount_x_contents)
                                remaining_contents = item.amount_x_contents - item_amount # vähennä lisätyt tuotteet jäljellä olevista varastossa olevista tuotteista
                                print('remaining_contents', remaining_contents)
                                new_amount = remaining_contents // item.contents # jako ilman jäännöstä. Se on uusi pakkausten määrä
                                print('new_amount', new_amount)
                                remainder = remaining_contents - (item.contents * new_amount)
                                print('remainder', remainder.normalize())

                                item.amount = new_amount
                                item.amount_x_contents = remaining_contents
                                kwargs['amount'] = None
                                kwargs['contents'] = item_amount
                                kwargs['units'] = item.unit

                            item.save() # Päivitetään tavaoiden määrä varastossa
                        except:
                            raise Exception(f'Tavara {item.id} ei riitä varastossa')
                    else:
                        error[4] = 'Error: Ei tarpeeksi tuotteita varastossa'

                rental = Rental_event(**kwargs) # Lisätään kaikki kentät tietokantaan. Jos lisättävää tavaraa ei ole kulutusmateriaalia, niin contents, amount_x_contents kentillä ovat None
                rental.save()
            changed_user = None
            changed_items = []
            return redirect('renter', idx=renter.id)
        else:
            error[6] = 'Kaikkia kenttiä ei ole täytetty'
            feedback_status = False

    # print('changed_user ', changed_user)
    # print('changed_items ', changed_items)

    # items = Goods.objects.all().order_by("id")
    storage_filter = storage_f(request.user)
    items = Goods.objects.filter(**storage_filter).order_by("id")
    paginator = Paginator(items, 20) # Siirtää muuttujan asetukseen

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'changed_user': changed_user,
        'changed_items': changed_items,
        'estimated_date': estimated_date,
        'estimated_date_issmall': estimated_date_issmall,
        'items': page_obj,
        'feedback_status': feedback_status,
    }
    # print(context)
    return render(request, 'varasto/new_event.html', context)


# FUNC is_ajax
def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


# FUNC getPersons
@login_required()
def getPersons(request):
    json_persons = []
    if is_ajax(request=request):
        if len(request.GET.get('name')) > 1:
            persons = CustomUser.objects.filter(
                Q(first_name__icontains=request.GET.get('name')) | 
                Q(last_name__icontains=request.GET.get('name')) | 
                Q(code__icontains=request.GET.get('name')))[:10]
            for person in persons:
                item = {
                    'id': person.id,
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'code': person.code,
                }
                json_persons.append(item) # Make response in json 
    return JsonResponse({'persons': json_persons})


# FUNC getProduct
@login_required()
def getProduct(request):
    json_goods = []
    if is_ajax(request=request):
        if len(request.GET.get('name')) > 1:
            products = Goods.objects.filter(
                Q(id__icontains=request.GET.get('name')) | 
                Q(item_name__icontains=request.GET.get('name')) | 
                Q(brand__icontains=request.GET.get('name')) | 
                Q(model__icontains=request.GET.get('name'))).order_by("id")[:10]
            for product in products:
                item = {
                    'id': product.id,
                    'item_name': product.item_name,
                    'brand': product.brand,
                    'model': product.model,
                    'ean': product.ean,
                }
                json_goods.append(item) # Make response in json 
    return JsonResponse({'goods': json_goods})


# FUNC getProducts
@login_required()
def getProducts(request):
    data = []
    if is_ajax(request=request):
        # items = Goods.objects.all().order_by("id")
        storage_filter = storage_f(request.user)
        items = Goods.objects.filter(**storage_filter).order_by("id")
        paginator = Paginator(items, 20) # Siirtää muuttujan asetukseen

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        for obj in page_obj:
            item = {
                'id': obj.id,
                'picture': settings.STATIC_URL + str(obj.picture),
                'item_name': obj.item_name if obj.item_name else '',
                'brand': obj.brand if obj.brand else '',
                'model': obj.model if obj.model else '',
                'item_type': obj.item_type if obj.item_type else '',
                'parameters': obj.parameters if obj.parameters else '',
                'size': obj.size if obj.size else '',
                'package': obj.contents if obj.contents else '',
                'ean': obj.ean if obj.ean else '',
                'rentable_at': obj.rentable_at if obj.rentable_at else '',
                'storage_place': obj.storage_place if obj.storage_place else '',
                'storage_name': obj.storage.name if obj.storage else '', # if in Goods table is no goods.storage_id getting error when try get obj.storage.name, because name isn't in storage
                'cat_name_id': obj.cat_name_id if obj.cat_name_id else '',
                'amount': obj.amount if obj.amount else '',
                'contents': obj.contents if obj.contents else '',
                'amount_x_contents': obj.amount_x_contents.normalize() if obj.amount_x_contents else '',
                'unit': obj.unit.unit_name if obj.unit else '',
            }
            data.append(item)
            print(settings.STATIC_URL + str(obj.picture))
    return JsonResponse({'items': data, })


# FUNC login_view
def login_view(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user) # не логинить, если не прошел проверку
                # if user_check(user) and is_not_student(user):
                if user.is_authenticated and user.is_staff:
                    return redirect(get_rental_events_page())
                    # return redirect('rental_events')
                # elif not is_not_student(request.user):
                #     return redirect('products')
                else:
                    # return redirect('logout')
                    return HttpResponse(f"<html><body><h1>Ei ole okeuksia päästä järjestelmään</h1><a href='/logout'>Logout1</a></body></html>") # Tässä voimme tehdä Timer, 10 sec jälkeen tehdään LOGOUT
            else:
                # Pitää rakentaa frontendilla vastaus, että kirjoitettu salasana tai tunnus oli väärin
                return redirect('login')
                # return HttpResponse("<html><body><h1>error</h1></body></html>")
        else:
            form = CustomUserForm()
            context = {
                'form': form,
                }
            return render(request, 'varasto/login.html', context)
    else:
        # if user_check(request.user) and is_not_student(request.user):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect(get_rental_events_page())
            # return redirect('rental_events')
        # elif not is_not_student(request.user):
        #     return redirect('products')
        else:
            # return redirect('logout')
            return HttpResponse("<html><body><h1>Ei ole okeuksia päästä järjestelmään</h1><a href='/logout'>Logout2</a></body></html>") # Tässä voimme tehdä Timer, 10 sec jälkeen tehdään LOGOUT

# FUNC logout
def logout_view(request):
    logout(request)
    return redirect('login')

def recovery_view(request):
    if request.user.is_authenticated:
        return redirect('login')
    return render(request, 'varasto/recovery.html')

def index(request):
    return redirect('login')

def user_recovery(request):
    return render(request, 'varasto/recovery.html')

def base_main(request):
    return render(request, 'varasto/base_main.html')

def update_rental_status(request):
    return render(request, 'varasto/update_rental_status.html')


# FUNC rental_events_goods
@login_required()
@user_passes_test(lambda user:user.is_staff)
def rental_events_goods(request):
    # Filteroi storage nimen mukaan, jos käyttäjillä Superuser oikeus niin näytetään kaikki tapahtumat kaikista varastoista
    storage_filter = storage_f(request.user)
    start_date_range = start_date_filter(request.GET.get('rental_start'), request.GET.get('rental_end'))
    order_filter = ['-'+order_field()[0], 'renter'] if order_filter_switch() else [order_field()[0], 'renter']
    print(start_date_range)

    events = Rental_event.objects.filter(returned_date__isnull=True).filter(**storage_filter).filter(**start_date_range).order_by(*order_filter)

    first_date = events[0].start_date if not order_filter_switch() else events.reverse()[0].start_date
    last_date = events.reverse()[0].start_date if not order_filter_switch() else events[0].start_date

    paginator = Paginator(events, 20) # Siirtää muuttujan asetukseen
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'events': page_obj,
        'first_date': first_date,
        'last_date': last_date,
        'order_switcher': order_filter_switch(),
        'order_field': order_field()[1],
        'all_order_fields': RENTAL_PAGE_ORDERING_FIELDS_D,
    }
    return render(request, 'varasto/rental_events_goods.html', context)


# FUNC rental_events
# @user_passes_test(is_not_student, redirect_field_name=None)
@login_required()
@user_passes_test(lambda user:user.is_staff)
# @user_passes_test(lambda user: user.has_perm('varasto.view_rental_event'))
def rental_events(request):
    # FIXID in is_user_have_non_returned_item property. When renter get product in another storage his mark may be red, if one of storage he has not returned products. Marker needs highlight by storage.
    storage_filter = storage_f(request.user)
    start_date_range = start_date_filter(request.GET.get('rental_start'), request.GET.get('rental_end'))
    select_order_field = order_field()[0].replace("__", ".") # Korvataan __ merkki . :hin, koska myöhemmin käytetään sorted()
    all_order_fields_nolast = RENTAL_PAGE_ORDERING_FIELDS_D.copy() # Kloonataan dictionary
    all_order_fields_nolast.pop(list(RENTAL_PAGE_ORDERING_FIELDS_D.keys())[-1]) # Poistetaan viimeinen elementti sanakirjasta (item__brand). Koska emme voi lajitella groupiroitu lista brandin kentän mukaan
    # print(RENTAL_PAGE_ORDERING_FIELDS_D)

    renters_by_min_startdate = Rental_event.objects.values('renter').filter(returned_date__isnull=True).filter(**storage_filter).filter(**start_date_range).annotate(mindate=Max('start_date')).order_by('renter')
    events = Rental_event.objects.filter(returned_date__isnull=True).filter(**storage_filter).filter(**start_date_range).order_by('renter', '-start_date')
    grouped_events1 = (
        Rental_event.objects
        .filter(returned_date__isnull=True)
        .filter(**storage_filter)
        .filter(**start_date_range)
        .filter(
            Q(start_date__in=renters_by_min_startdate.values('mindate')) & 
            Q(renter__in=renters_by_min_startdate.values('renter'))
        )
        .order_by('renter')
        .distinct('renter')
    )
    # grouped_events = sorted(grouped_events1, key=operator.attrgetter('start_date'), reverse=order_filter_switch())
    grouped_events = sorted(grouped_events1, key=operator.attrgetter(select_order_field), reverse=order_filter_switch())

    paginator = Paginator(grouped_events, 20) # Siirtää muuttujan asetukseen
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'grouped_events': page_obj,
        'events': events,
        'order_switcher': order_filter_switch(),
        'order_field': order_field()[1],
        'all_order_fields': all_order_fields_nolast,
    }
    return render(request, 'varasto/rental_events.html', context)


# FUNC new_user
# @login_required()
# @user_passes_test(lambda user:user.is_staff)
# def new_user(request):
#     return render(request, 'varasto/new_user.html')


# FUNC get_photo
def get_photo(request):
    picData = request.POST.get('picData')
    img = _save_image(picData)
    print(img)
    return HttpResponse("<html><body><h1>SAVED</h1></body></html>") 


# FUNC edit_item
@login_required()
@user_passes_test(lambda user:user.is_staff)
@user_passes_test(lambda user: user.has_perm('varasto.change_goods'))
# @user_passes_test(is_same_storage, redirect_field_name='product')
def edit_item(request, idx):
    storage_filter = storage_f(request.user) # if storage_filter is empty means superuser, management or student
    try:
        item = Goods.objects.get(id=idx)
        print(item.storage, request.user.storage)
        if item.storage != request.user.storage and storage_filter: 
            error = "Voi muokata vain tavaroita sijäitsevä sama varastossa"
            return redirect('product', idx=idx)
    except:
        pass
    
    l = []
    error_massage = ''
    camera_picture = request.POST.get('canvasData')
    get_item = Goods.objects.get(id=idx)
    unit = get_item.unit
    cat_name = get_item.cat_name
    cat_name_id = get_item.cat_name_id
    storage = get_item.storage
    amount = get_item.amount
    contents = get_item.contents

    if request.method == "POST":
        form = GoodsForm(request.POST, request.FILES, instance=get_item)
        if form.is_valid():
            item = form.save(commit=False)
            print('item.picture=', item.picture)
            try:
                if not item.picture:
                    new_picture = PRODUCT_IMG_PATH + _save_image(camera_picture, request.POST.get('csrfmiddlewaretoken'))
                else:
                    new_picture = request.FILES['picture']
                item.picture = new_picture
            except:
                print('get_item.picture=', get_item.picture)
            # FIXME Yksikko перенести в поле MÄÄRÄ PAKKAUKSESSA, а на освободившееся место поставить поле amount_x_contents
            if cat_name_id == CATEGORY_CONSUMABLES_ID:
                print('item.amount_x_contents', item.amount_x_contents)
                if (item.amount - amount) > 0:
                    new_amount_x_contents = (item.amount - amount) * contents
                    item.amount_x_contents += new_amount_x_contents
                if (item.amount - amount) < 0:
                    new_amount_x_contents = (amount - item.amount) * contents
                    item.amount_x_contents -= new_amount_x_contents

            item.contents = contents # Ei saa muokata contents
            item.cat_name = cat_name
            item.unit = unit
            item.storage = storage if not item.storage else item.storage

            form.save()
            return redirect('product', idx)
        else:
            return HttpResponse('form not valid')
    else:        
        form = GoodsForm(instance=get_item)

    
    # permission_group = request.user.groups.get()
    
    # storage_employee and student_ext can't edit all fields
    if request.user.groups.filter(name='storage_employee').exists() or request.user.groups.filter(name='student_ext').exists():
        is_storage_employee = ['readonly', 'disabled']
    else:
        is_storage_employee = ['', '']
    print(is_storage_employee)

    event = Rental_event.objects.filter(item_id=idx).filter(returned_date=None)
    is_rented = False
    if event:
        is_rented = True

    context = {
        'form': form,
        'item': get_item,
        'is_storage_employee': is_storage_employee,
        'is_rented': is_rented,
        'error_massage': error_massage
    }
    return render(request, 'varasto/edit_item.html', context)

# FUNC new_item
@login_required()
@user_passes_test(lambda user: user.has_perm('varasto.add_goods'))
def new_item(request):
    l = []
    error_massage = ''
    camera_picture = request.POST.get('canvasData')

    if request.method == "POST":
        print('request.POST')
        print("csrfmiddlewaretoken", request.POST.get('csrfmiddlewaretoken'))
        form = GoodsForm(request.POST, request.FILES)
        if form.is_valid():
            print('FORM is VALID')
            item = form.save(commit=False)
            if camera_picture:
                new_picture = PRODUCT_IMG_PATH + _save_image(camera_picture, request.POST.get('csrfmiddlewaretoken'))
            elif 'picture' in request.FILES:
                new_picture = request.FILES['picture']
            else:
                new_picture = None

            if item.cat_name:
                if not item.cat_name.id == CATEGORY_CONSUMABLES_ID: # Jos kategoria ei ole Kulutusmateriaali lähetetään kaikki kappalet eri kentään
                    l += item.amount * [item] # luo toistuva luettelo syötetystä (item.amount) määrästä tuotteita
                    item.amount = 1 # Nollataan amount
                    item.contents = 1
                    item.picture = new_picture
                    item.amount_x_contents = None
                    Goods.objects.bulk_create(l) # Lähettää kaikki tietokantaan
                else:
                    # item.cat_name = None
                    # item.contents = None
                    item.picture = new_picture
                    item.amount_x_contents = Decimal(request.POST.get('amount')) * Decimal(request.POST.get('contents'))
                    item.save() # Jos kategoria ei ole Kulutusmateriaali lähetetään kaikki kappalet sama kentään
                    form.save()
            else:
                error_massage = "Ei valittu kategoriaa"
        
        return redirect('new_item')
    else:
        form = GoodsForm(use_required_attribute=False, initial={'storage': request.user.storage})

    context = {
        'form': form,
        'error_massage': error_massage
    }
    return render(request, 'varasto/new_item.html', context)


# FUNC products
@login_required()
def products(request):
    # Try get a number from checkbox "näytä kaikki"
    try:
        get_show_all = int(request.GET.get('show_all'))
    except:
        get_show_all = 1 # If got exeption, then we show all products from db
    
    if get_show_all: # if got any simbol(s), then show all products
        is_show_all = 1
        storage_filter = {}
    else: # if got 0 show products from same storage where storage employee from
        is_show_all = 0
        storage_filter = storage_f(request.user)# Jos checkbox "Näytä kaikki" ei ole valittu näytetään tavarat sama varastossa, jossa varastotyöntekijällä on valittu
    
    items = Goods.objects.filter(**storage_filter).order_by("id")
    paginator = Paginator(items, 20) # Siirtää muuttujan asetukseen

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'items': page_obj,
        'is_show_all': is_show_all,
    }
    return render(request, 'varasto/products.html', context)


# FUNC product
@login_required()
@user_passes_test(lambda user:user.is_staff)
# @user_passes_test(lambda user: user.has_perm('varasto.change_goods'))
def product(request, idx):
    user = request.user
    rental_events = None
    selected_item = Goods.objects.get(id=idx)
    # if user.has_perm('varasto.view_customuser'):
    rental_events = Rental_event.objects.filter(item=selected_item).order_by('-start_date')

    paginator = Paginator(rental_events, 10) # Siirtää muuttujan asetukseen
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'rental_events': page_obj,
        'selected_item': selected_item,
        'idx': idx,
    }
    return render(request, 'varasto/product.html', context)


# FUNC set_rental_event_view
@login_required()
def set_rental_event_view(request):
    # if 'name' in request.GET:
    #     print('request.GET name =', request.GET.get('name'))

    set = Settings.objects.get(set_name='rental_page_view')
    set.set_value = request.GET.get('name')
    set.save()

    return redirect (request.GET.get('name'))


# FUNC set_ordering
@login_required()
def set_ordering(request):
    set = Settings.objects.get(set_name='rental_page_ordering')
    order = 0 if int(set.set_value) else 1
    set.set_value = order
    set.save()

    page = Settings.objects.get(set_name='rental_page_view')
    return redirect (page.set_value)


# FUNC set_order_field
@login_required()
def set_order_field(request):
    set = Settings.objects.get(set_name='rental_page_field_ordering')
    set.set_value = request.GET.get('order')
    set.save()

    page = Settings.objects.get(set_name='rental_page_view')
    return redirect (page.set_value)

@login_required()
def delete_product(request, idx):
    staff = CustomUser.objects.get(id=request.user.id)
    item = Goods.objects.get(id=idx)
    item_data_dict = item.__dict__.copy() # Make copy of product instance

    # Delete unnecessary fields in product info
    entries_to_remove = ('_state', 'cat_name_id', 'item_type', 'size', 'parameters', 'item_description', 'picture', 'storage_place', 'item_status', 'cost_centre', 'purchase_data', 'purchase_price', 'purchase_place', 'storage_id', 'cat_name_id', 'ean')
    for k in entries_to_remove:
        item_data_dict.pop(k, None)
    item_data_dict['contents'] = str(item.contents.normalize()) if item.contents else ''
    item_data_dict['amount_x_contents'] = str(item.amount_x_contents.normalize()) if item.amount_x_contents else ''
    print(item_data_dict)

    user_dict = staff.__dict__.copy() # Make copy of staff instance
    # Delete unnecessary fields in product info
    entries_to_remove = ('_state', 'username', 'password', 'email', 'last_login', 'date_joined', 'is_superuser', 'is_staff', 'is_active', 'group', 'photo', 'role', 'responsible_teacher_id', 'storage_id')
    for k in entries_to_remove:
        user_dict.pop(k, None)
    print(user_dict)

    # Create record about event in Staff_audit table
    storage = request.user.storage.name if request.user.storage else None
    now = datetime.now()
    datenow = pytz.utc.localize(now)
    staff_audit = Staff_audit.objects.create(
        staff = user_dict,
        item = item_data_dict,
        event_process = 'Delete item',
        to_storage = storage,
        event_date = datenow,
    )
    staff_audit.save()
    
    item.delete()

    # TODO Redirect to same page where product was
    return redirect("products")

@login_required()
def burger_settings(request):
    show_full = request.POST.get('show_full')

    try:
        burger_setting_dict = Settings.objects.get(set_name='show_full_burger')
        burger_setting_dict.set_value = show_full
    except Settings.DoesNotExist:
        burger_setting_dict = Settings(set_name='show_full_burger', set_value=show_full)
    finally:
        burger_setting_dict.save()

    show_full_burger = burger_setting_dict.set_value
    # burger_dict = burger_dict.replace("\'", "\"")
    # burger_settings_json = json.loads(burger_dict)

    return JsonResponse({'show_full_burger': show_full_burger, })



# FUNC filling_storage_place
# storage_place sarakkeen täyttäminen
def filling_storage_place(request):
    items = Goods.objects.all().order_by("ean")
    rack = ['A', 'B', 'C']
    rackid = 0
    unit = 1
    shelf = 0

    for item in items:
        if shelf < 9:
            shelf += 1
        elif unit < 9:
            unit += 1
            shelf = 1
        elif rackid < 3:
            rackid += 1
            unit = 1
            shelf = 1
        else:
            rackid = 1
            unit = 1
            shelf = 1

        print(rack[rackid]+str(unit)+str(shelf))
        # item.storage_place = rack[rackid]+str(unit)+str(shelf)
        # item.save()
    
    return HttpResponse("<html><body><h1>RENDERED</h1></body></html>")


# FUNC filling_goods_description
 # Adding description to products from 2-12 fields
def filling_goods_description(request):
    items = Goods.objects.filter(id__in=[2,3,4,5,6,7,8,9,10,11,12])
    # for item in items:
    #     print(item.id)
    #     print(item.item_description)

    n = 0
    new_items = Goods.objects.all().order_by("id")
    for new_item in new_items:
        if new_item.id > 12:
            # new_item.item_description = items[n].item_description
            # new_item.save()
            print(items[n].item_description)
        if n < 10:
            n += 1
        else:
            n = 0

    return HttpResponse("<html><body><h1>RENDERED</h1></body></html>")
    

