from django.db import models
import requests
from django.db.models import Q
from datetime import timedelta

def items_arrived(self):
    from .models import Job, JobItem
    all_arrived=False
    if self.pk:
        if isinstance(self,Job) and self.items.all().count()>0:
            all_arrived = all(
                    item.arrived or item.from_warehouse
                    for item in self.items.all()
                )
            
            self.items_arrived=all_arrived 
        elif isinstance(self,Job) :
            all_arrived=True
            self.items_arrived=all_arrived 
        elif isinstance(self,JobItem):
            all_arrived = all(
                    item.arrived or item.from_warehouse
                    for item in self.job.items.all()
                )
    return all_arrived

def items_not_used(self):
    from .models import Job, JobItem
    not_used=False
    if self.pk:
        if isinstance(self,Job) and self.items.all().count()>0:
            not_used = all(
                    not item.is_used
                    for item in self.items.all()
                )
            self.items_arrived=not_used 
        elif isinstance(self,Job) :
            not_used=True
            self.items_arrived=not_used 
        elif isinstance(self,JobItem):
            not_used = all(
                    not item.is_used
                    for item in self.job.items.all()
                )
    return not_used



def job_reopened(self,):
    if self.pk:
        old_instance = type(self).objects.get(pk=self.pk)
        old_status = old_instance.status
        if (self.status != "completed" and old_status == "completed" and self.status != "cancelled") or (self.status != "cancelled" and old_status == "cancelled" and self.status != "completed") :
                for item in self.items.all():
                    if item.is_used:
                        item.was_it_used=True
                        item.save(update_fields=['was_it_used'],no_recursion=True,request=None)
                return True
        return False
def quote_accepted(self,):
    if self.pk:
        if self.quoted:
            if self.quote_accepted:
                return True
            return False
        return True
    return False
def item_arrived(self):
    if self.from_warehouse:
        
        return True
    if self.ordered:
            if self.arrived_quantity >= self.job_quantity:
                self.arrived = True
            else:
                self.arrived=False
    else:
        self.arrived = False
    return self.arrived
def item_not_used(self):
    return self.is_used
def job_completed(self,):
    if self.status=='completed':
        for item in self.items.all():
            item.is_used=True
            item.save(update_fields=['is_used'],no_recursion=True,request=None)
        
        return True
    return False


def generate_otp():
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase  + string.digits, k=6))
    # if user:
    #     user.otp=code
    #     user.save(update_fields=['otp'])
    return code
def send_otp_email(email, otp):
    from django.core.mail import send_mail
    from django.conf import settings
    send_mail(
        subject='Your OTP Code',
        message=f'Your OTP code is {otp}',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
def send_guest_email(email, login_email,password):
    from django.core.mail import send_mail
    from django.conf import settings
    send_mail(
        subject='Stocky login credentials',
        message=f'Welcome to Stock, \n Your login details \n Email: {login_email} \n Password: {password} ',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
from django.core.mail import send_mail
from django.conf import settings

from collections import defaultdict
from django.utils import timezone
def send_multiple_emails(jobs, request=None,single=False,):
    
    # Group jobs by engineer
    engineer_jobs = defaultdict(list)
    for job in jobs:
        if job.engineer:
            engineer_jobs[job.engineer].append(job)

    # Send one email to each engineer
    for engineer, jobs_list in engineer_jobs.items():
        message_lines = [f"Hi {engineer.name}, please take the following parts for :\n"]
        
        for job in jobs_list:
            parts = [str(part)+str(("("+"x"+str(part.job_quantity)+")")) for part in job.items.all()]
            if parts:
                parts_text = ", ".join(parts)
            else:
                parts_text = "No parts assigned."
            message_lines.append(f"Job {job.address}:\n{parts_text}\n")

        full_message = "\n".join(message_lines)
        
        send_mail(
            subject=f"Your Job Parts List for{job.date}",
            message=full_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[engineer.email],  # Assumes `engineer.email` exists
            fail_silently=False,
        )
        from .models import Email
        user=request.user
        company=request.user.company    
        if single:
            Email.objects.create(type=Email.EmailType.SINGLE,company=company,user=user,to=engineer.name,subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)
        else:
            
            Email.objects.create(type=Email.EmailType.BATCH,company=company,user=user,to=engineer.name,subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)



def get_access_token(company):
    SF_CLIENT_ID = company.settings.sf_client_id
    SF_CLIENT_SECRET = company.settings.sf_client_secret
    if not SF_CLIENT_ID or not SF_CLIENT_SECRET:
        raise Exception ("Missing Client ID or Client Secret")
    if (
        not company.settings.sf_access_token
        or not company.settings.sf_refresh_token
        or company.settings.sf_token_expires <= timezone.now()
    ):
        url = "https://api.servicefusion.com/oauth/access_token"
        data = {
        "grant_type": "client_credentials",
        "client_id":SF_CLIENT_ID ,
        "client_secret": SF_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/json"}
        resp=requests.post(url, json=data, headers=headers )
        if resp.status_code == 200 :
            tokens = resp.json()
            company.settings.sf_access_token=tokens["access_token"]
            company.settings.sf_token_expires=timezone.now() + timedelta(seconds=tokens["expires_in"])
            company.settings.sf_refresh_token=tokens.get("refresh_token")
            company.settings.save()
            return company.settings.sf_access_token
        else:
            raise Exception(f"Failed to refresh token: {resp.text}")
    return company.settings.sf_access_token


def refresh_sf_token(company):
    SF_CLIENT_ID = company.settings.sf_client_id
    SF_CLIENT_SECRET = company.settings.sf_client_secret
    SF_REFRESH_TOKEN=company.settings.sf_refresh_token
    url = "https://api.servicefusion.com/oauth/access_token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SF_REFRESH_TOKEN,
        "client_id": SF_CLIENT_ID,
        "client_secret": SF_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/json"}

    resp = requests.post(url, json=data, headers=headers)
    if resp.status_code == 200:
        tokens = resp.json()
        company.settings.sf_access_token = tokens["access_token"]
        company.settings.sf_token_expires = timezone.now() + timedelta(seconds=tokens["expires_in"])
        # Some APIs return a new refresh token too
        if "refresh_token" in tokens:
            company.settings.sf_refresh_token = tokens["refresh_token"]
        company.settings.save()
        return company.settings.sf_access_token
    else:
        raise Exception(f"Failed to refresh token: {resp.text}")


def sync_engineers_func(request):

    from .models import Engineer
    url = "https://0350b95b-a46f-4716-94c8-b6677b1f904f.mock.pstmn.io/engs"
    headers = {"Authorization": f"Bearer {request.user.company.sf_access_token}"}
    response = requests.get(url, headers=headers)


    if response.status_code == 401:
        new_token = refresh_sf_token(request.user.company)
        headers = {"Authorization": f"Bearer {new_token}"}
        response = requests.get(url, headers=headers)
    data=response.json()
    
    for eng in data:
        email=eng["email"]
        try:
            ex_eng=Engineer.objects.get(Q(company=request.user.company) & Q(email=eng["email"]))
            if ex_eng.sf_id != eng["id"]:
                ex_eng.sf_id=eng["id"]
                ex_eng.save(update_fields=['sf_id'],request=request)    
        except Engineer.DoesNotExist:
            eng = Engineer(
                company=request.user.company,
                email=email,
                name=f'{eng["first_name"]} {eng["last_name"]}',
                phone=eng["phone_1"],
                sf_id=eng["id"],
                )
            eng.save(request=request,affected_by_sync=True)


def update_if_changed(instance: models.Model, d: dict, field_map: dict, *,request=None, affected_by_sync=False, ignore_empty=False):
    """
    Update Django model instance only if one or more mapped fields differ from the new data.
    
    Args:
        instance: The Django model instance to update.
        data: Incoming data (from API, payload, etc.).
        field_map: Dict mapping model fields → callable(data) returning new value.
        request: Optional, passed to .save() if your model overrides save().
        afected_by_sync: Optional flag for custom save logic.
        ignore_empty: If True, ignores blank/None values from data.
    
    Returns:
        list: Names of changed fields (empty if no change).
    """
    changed_fields = []

    for field, get_val in field_map.items():
        try:
            # if field=="date" or field=="birthday":
            #     new_val = get_val(d).date()
            # elif field=="from_time" or field=="to_time":
            #     new_val = get_val(d).datetime()
            # else:
            new_val = get_val(d)
        except Exception as e:
            continue

        old_val = getattr(instance, field)

        # Optional cleanup for strings
        if isinstance(new_val, str):
            new_val = new_val.strip()
        if isinstance(old_val, str):
            old_val = old_val.strip()

        # Optionally skip empty values
        if ignore_empty and (new_val in ("", None)):
            continue

        # Compare & update
        if old_val != new_val:
            setattr(instance, field, new_val)
            changed_fields.append(field)

    # Save only if something actually changed
    if changed_fields:
        instance.save(
            update_fields=changed_fields,
            request=request,
            affected_by_sync=affected_by_sync
        )
        print(f"✅ {instance.__class__.__name__} {getattr(instance, 'id', '')} updated — {changed_fields}")
    else:
        print(f"⏩ {instance.__class__.__name__} {getattr(instance, 'id', '')} skipped — no changes detected.")

    return changed_fields
import requests
import random
import time
from math import radians, cos, sin, asin, sqrt,atan2
from functools import lru_cache
from decouple import config

# --- API Key ---
API_KEY = config("ORS_API_KEY", default="your_api_key_here")

# --- Get coordinates from postcode ---
def get_coords(postcode):
    """Fetch approximate coordinates from postcodes.io"""
    try:
        res = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
        if res.status_code == 200:
            data = res.json().get("result")
            if data:
                return data["latitude"], data["longitude"]
    except Exception:
        pass
    return None, None


# --- Haversine fallback (km) ---
from math import radians, sin, cos, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance (in km) between two GPS points."""
    R = 6371  # Earth's radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c



# --- Cache of drive times ---
drive_cache = {}

@lru_cache(maxsize=512)
def get_drive_time_ors(origin_lat, origin_lon, dest_lat, dest_lon):
    """Returns driving duration in minutes using OpenRouteService with fallback."""
    origin_lat, origin_lon = round(origin_lat, 5), round(origin_lon, 5)
    dest_lat, dest_lon = round(dest_lat, 5), round(dest_lon, 5)
    key = (origin_lat, origin_lon, dest_lat, dest_lon)
    if key in drive_cache:
        return drive_cache[key]

    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": API_KEY}
    params = {"start": f"{origin_lon},{origin_lat}", "end": f"{dest_lon},{dest_lat}"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=6)
        r.raise_for_status()
        data = r.json()
        duration_sec = data["features"][0]["properties"]["summary"]["duration"]
        minutes = duration_sec / 60
        drive_cache[key] = minutes
        return minutes
    except Exception:
        # fallback if API fails
        km = haversine(origin_lat, origin_lon, dest_lat, dest_lon)
        est_time = (km / 40) * 60
        drive_cache[key] = est_time
        return est_time


# --- Helper: route total time ---
def route_total_time(route):
    total = 0
    for i in range(len(route) - 1):
        total += get_drive_time_ors(
            route[i].latitude, route[i].longitude,
            route[i + 1].latitude, route[i + 1].longitude
        )
    return total


# --- 2-opt Improvement ---
def two_opt(route):
    improved = True
    while improved:
        improved = False
        for i in range(1, len(route) - 2):  
            for j in range(i + 1, len(route)):
                if j - i == 1:
                    continue
                new_route = route[:]
                new_route[i:j] = route[j - 1:i - 1:-1]
                if route_total_time(new_route) < route_total_time(route):
                    route = new_route
                    improved = True
        time.sleep(0.01)
    return route


# --- Genetic Algorithm Optimization ---

def optimize_group_order(jobs):
    """Optimize job order by travel time using ORS, fallback to greedy method."""
    if not jobs or len(jobs) == 1:
        return list(jobs)

    # ✅ Use first job as start & end point
    start_job = jobs[0]

    # 🧠 Prepare job data for ORS
    jobs_data = []
    for i, job in enumerate(jobs):
        if job.latitude is None or job.longitude is None:
            continue
        jobs_data.append({
            "id": i + 1,
            "location": [float(job.longitude), float(job.latitude)],
            "service": 300  # 5 minutes per stop (optional)
        })

    if not jobs_data:
        return list(jobs)

    # 🧠 Vehicle definition
    vehicles = [{
        "id": 1,
        "profile": "driving-car",  # ✅ FIXED (was 'car')
        "start": [float(start_job.longitude), float(start_job.latitude)],
        "end": [float(start_job.longitude), float(start_job.latitude)],
    }]

    # 📦 API request body
    body = {"jobs": jobs_data, "vehicles": vehicles}

    try:
        response = requests.post(
            "https://api.openrouteservice.org/optimization",
            json=body,
            headers={"Authorization": API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        # ✅ Parse optimized order
        steps = data["routes"][0]["steps"]
        optimized_indices = [step["job"] - 1 for step in steps if "job" in step]
        optimized = [jobs[i] for i in optimized_indices if i < len(jobs)]

        print("✅ ORS Optimization successful! Order:", [j.id for j in optimized])
        return optimized

    except Exception as e:
        print(f"❌ ORS Optimization API failed: {e}")
        try:
            err = response.json()
            print(f"🧠 ORS says: {err}")
        except:
            pass
        print("⚠️ Fallback to local greedy optimization.\n")

        # -------------------------------
        # 🚗 Greedy Fallback Optimizer
        # -------------------------------
        optimized = [jobs[0]]
        remaining = list(jobs[1:])
        while remaining:
            last = optimized[-1]
            best_job = min(
                remaining,
                key=lambda j: haversine(
                    last.latitude, last.longitude, j.latitude, j.longitude
                ),
            )
            optimized.append(best_job)
            remaining.remove(best_job)

        print("✅ Local Greedy Fallback Order:", [j.id for j in optimized])
        return optimized
    

from itertools import groupby
import requests

def optimize_group_order2(jobs):
    
    """Optimize job order using LocationIQ Optimize API, grouping same-postcode jobs together and slightly offsetting coordinates."""
    if not jobs or len(jobs) == 1:
        return list(jobs)
    

    # ✅ Step 1: Group jobs by postcode (keeping their internal order)
    jobs.sort(key=lambda j: (j.post_code or "").strip().upper())
    grouped = [list(g) for _, g in groupby(jobs, key=lambda j: (j.post_code or "").strip().upper())]
    print(f"📦 Grouped into {len(grouped)} postcode clusters")

    # ✅ Step 2: Prepare representative coordinates for each group, with tiny offset
    coords, group_reps = [], []
    for idx, group in enumerate(grouped):
        rep = next((j for j in group if j.latitude is not None and j.longitude is not None), None)
        if rep:
            # Apply unique micro-offset to avoid identical coordinates
            lon_offset = float(f"0.000{idx+1}")
            lat_offset = float(f"0.000{idx+2}")
            adj_lon = rep.longitude + lon_offset
            adj_lat = rep.latitude + lat_offset

            coords.append(f"{adj_lon},{adj_lat}")
            group_reps.append(group)

    if not coords:
        print("⚠️ No valid coordinates found, skipping optimization.")
        return list(jobs)

    # ⚠️ Limit due to free-tier restriction
    if len(coords) > 10:
        print(f"⚠️ Too many postcode clusters ({len(coords)}). Using greedy fallback.")
        return _greedy_fallback(jobs)

    try:
        coord_str = ";".join(coords)
        print("🧭 Coordinates (with tiny offsets):", coord_str)
        url = f"https://us1.locationiq.com/v1/optimize/driving/{coord_str}"
        params = {
            "key": "pk.9f0369e994b0fcf9da50cf62c971aa40oo",
            "roundtrip": "false"
        }

        res = requests.get(url, params=params, timeout=30)
        res.raise_for_status()
        data = res.json()
        print("📦 LocationIQ Response:", data)

        # ✅ Validate response
        if not data.get("trips") or not data.get("waypoints"):
            raise ValueError("Invalid response structure (missing 'trips' or 'waypoints').")

        trip = data["trips"][0]

        # ✅ Extract optimized order indexes
        order_indexes = trip.get("waypoint_order")
        if not order_indexes:
            order_indexes = [wp["waypoint_index"] for wp in data["waypoints"]]

        print("📍 Optimized postcode group order indexes:", order_indexes)

        # ✅ Map back to grouped jobs
        optimized_jobs = []
        for i in order_indexes:
            if i < len(group_reps):
                optimized_jobs.extend(group_reps[i])  # keep grouped jobs together

        if not optimized_jobs or len(optimized_jobs) != len(jobs):
            print("⚠️ Job count mismatch; using fallback.")
            return _greedy_fallback(jobs)

        print("✅ Optimized job order (grouped + offset):", [j.id for j in optimized_jobs])
        return optimized_jobs

    except Exception as e:
        print(f"❌ LocationIQ Optimization failed: {e}")
        if "res" in locals():
            try:
                print("🧠 Response JSON:", res.json())
            except Exception:
                print("⚠️ Could not parse error response.")
        return _greedy_fallback(jobs)

def _greedy_fallback(jobs):
    print("⚠️ Executing Greedy Fallback Optimizer...")

    # Split jobs into valid and invalid based on coordinates
    valid_jobs = [j for j in jobs if j.latitude is not None and j.longitude is not None]
    invalid_jobs = [j for j in jobs if j.latitude is None or j.longitude is None]

    if not valid_jobs:
        # All jobs invalid → return as is
        return jobs

    if len(valid_jobs) == 1:
        optimized = valid_jobs
    else:
        optimized = [valid_jobs[0]]
        remaining = list(valid_jobs[1:])

        while remaining:
            last = optimized[-1]
            valid_remaining = [j for j in remaining if j.latitude is not None and j.longitude is not None]
            if not valid_remaining:
                break

            best_job = min(
                valid_remaining,
                key=lambda j: haversine(last.latitude, last.longitude, j.latitude, j.longitude),
            )
            optimized.append(best_job)
            remaining.remove(best_job)

    # Append invalid jobs (unoptimized) at the end
    optimized.extend(invalid_jobs)
    print("✅ Greedy Fallback Order:", optimized)
    return optimized


#MOVE UP AND DOWN

def move (request,ex_sg,) :
    from .models import Job
    from django.db import transaction
    if request.method == "POST" :
        
        if "move_down" in request.POST:    
            job_id = int(request.POST.get("move_down"))
            group_id = int(request.POST.get("group_id"))
            group = ex_sg.get(id=group_id)
        
            # Convert stored job_order into a list of ints
            if isinstance(group.job_order, str):
                order = [int(x) for x in group.job_order.split(",") if x]
            else:
                order = list(group.job_order)
            try:
                index = order.index(job_id)
                # Swap with the next job if possible
                if index < len(order) - 1:
                    order[index], order[index + 1] = order[index + 1], order[index]
                    group.job_order=order
                    postcodes = [job.post_code.strip() for job in group.ordered_jobs() if job.post_code]
                    group.map_url = "https://www.google.com/maps/dir/" + "/".join(postcodes)    
                    group.save(update_fields=["job_order","map_url"])
            except ValueError:
                pass  # job_id not found in order list
        elif "move_up" in request.POST:
            job_id = int(request.POST.get("move_up"))
            group_id = int(request.POST.get("group_id"))
            group = ex_sg.get(id=group_id)

            # Convert stored job_order into a list of ints
            if isinstance(group.job_order, str):
                order = [int(x) for x in group.job_order.split(",") if x]
            else:
                order = list(group.job_order)
            try:
                index = order.index(job_id)
                # Swap with the previous job if possible
                if index > 0:
                    order[index], order[index - 1] = order[index - 1], order[index]
                    group.job_order=order
                    postcodes = [job.post_code.strip() for job in group.ordered_jobs() if job.post_code]
                    group.map_url = "https://www.google.com/maps/dir/" + "/".join(postcodes)    
                    group.save(update_fields=["job_order","map_url"])
            except ValueError:
                pass  # job_id not found in order list
            
        elif "new_group" in request.POST:
            
            old_group_id = int(request.POST.get("group_id"))
            new_group_id = int(request.POST.get("new_group"))
            job_id = int(request.POST.get("job_id"))
            old_group = ex_sg.get(id=old_group_id)
            new_group = ex_sg.get(id=new_group_id)

            old_group.save()
            
            job = Job.objects.get(company=request.user.company, id=job_id)

            with transaction.atomic():
                # Remove from old group
                old_group.jobs.remove(job)
                if job.id in old_group.job_order:
                    old_group.job_order.remove(job.id)
                    postcodes = [jobl.post_code.strip() for jobl in old_group.ordered_jobs() if jobl.post_code and jobl.id != job.id]
                    old_group.map_url = "https://www.google.com/maps/dir/" + "/".join(postcodes)    
                old_group.save(update_fields=["job_order","map_url"])

                # Add to new group
                new_group.jobs.add(job)
                if job.id not in new_group.job_order:
                    new_group.job_order.append(job.id)
                new_group.map_url=new_group.map_url+"/"+str(job.post_code)
                
                new_group.save(update_fields=["job_order","map_url"])
           