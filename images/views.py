from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings

import redis

from .forms import ImageCreateForm
from .models import Image
from actions.utils import create_action

r = redis.Redis(host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB)


@login_required
def image_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = ImageCreateForm(data=request.POST)
        if form.is_valid():
            new_image: Image = form.save(commit=False)
            new_image.user = request.user
            new_image.save()

            create_action(request.user, 'bookmarked image', new_image)

            messages.success(request, 'Image has been successfully added')

            return redirect(new_image.get_absolute_url())
    else:
        form = ImageCreateForm(data=request.GET)

    return render(request, 'images/image/create.html', {'form': form})


def image_detail(request, id, slug):
    image = get_object_or_404(Image, id=id, slug=slug)

    total_views = r.incr(f'image:{image.id}:views')
    return render(request,
                  'images/image/detail.html',
                  {'section': 'images', 'image': image,
                   'total_views': total_views})


@login_required
@require_POST
def image_like(request: HttpRequest):
    image_id = request.POST.get('id')
    action = request.POST.get('action')

    if image_id and action:
        try:
            image = Image.objects.get(id=image_id)
            if action == 'like':
                image.users_like.add(request.user)
                create_action(request.user, 'likes', image)
            else:
                image.users_like.remove(request.user)
            return JsonResponse({'status': 'ok'})
        except Image.DoesNotExist:
            pass
    return JsonResponse({'status': 'error'})


@login_required
def image_list(request: HttpRequest) -> HttpResponse:
    images = Image.objects.all()
    paginator = Paginator(images, 8)

    page = request.GET.get('page')
    images_only = request.GET.get('images_only')

    try:
        images = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer we deliver the first page
        images = paginator.page(1)
    except EmptyPage:
        if images_only:
            # If AJAX request and page out of range, return empty page
            return HttpResponse('')
        # if page is out of range return the last page of results
        images = paginator.page(paginator.num_pages)
    if images_only:
        return render(request,
                      'images/image/list_images.html',
                      {'section': 'images', 'images': images})
    return render(request,
                  'images/image/list.html',
                  {'section': 'images', 'images': images})

