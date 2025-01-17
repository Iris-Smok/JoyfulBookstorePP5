"""views for books app"""
# pylint: disable=locally-disabled, no-member
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.db.models import Avg
from profiles.models import UserProfile
from .forms import BookForm, CategoryForm, ReviewForm
from .models import Book, Category, Review


def all_books(request):
    """ A view to show all books, including sorting and searching queries"""

    books = Book.objects.all()
    query = None
    categories = None
    sort = None
    direction = None
    new = None
    sale = None
    price = None

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
            sort = sortkey

        if 'direction' in request.GET:
            direction = request.GET['direction']

            # Thanks to tutor Igor at Code Institute for tips on nulls_last
            if sortkey == 'rating':
                if direction == 'desc':
                    books = books.order_by(
                        F(sortkey).desc(nulls_last=True)
                    )
                else:
                    books = books.order_by(
                        F(sortkey).asc(nulls_first=True)
                    )
            else:
                if sortkey == 'name':
                    sortkey = 'lower_name'
                    books = books.annotate(lower_name=Lower('title'))
                if sortkey == 'category':
                    sortkey = 'category__name'

                if direction == 'desc':
                    sortkey = f'-{sortkey}'

                books = books.order_by(sortkey)

    if 'category' in request.GET:
        categories = request.GET['category'].split(',')
        books = books.filter(category__name__in=categories)
        # pylint: disable=no-member
        categories = Category.objects.filter(name__in=categories)

    if 'new' in request.GET:
        books = books.filter(is_new=True)
        new = True

    if 'on_sale' in request.GET:
        books = books.filter(~Q(sale_price=price))
        sale = True

    if 'q' in request.GET:
        query = request.GET['q']
        if not query:
            messages.error(
                request, "You didn't enter any search criteria!")
            return redirect(reverse('books'))

        queries = Q(
            title__icontains=query) | Q(description__icontains=query)
        books = books.filter(queries)

    current_sorting = f'{sort}_{direction}'

    context = {
        'books': books,
        'search_term': query,
        'current_categories': categories,
        "current_sorting": current_sorting,
        'new': new,
        'sale': sale,
    }
    return render(request, 'books/books.html', context)


def book_detail(request, book_id):
    """ A view to show book details"""

    book = get_object_or_404(Book, pk=book_id)
    reviews = Review.objects.all().filter(book=book).order_by('-created_on')
    review_count = len(reviews)

    if request.user.is_authenticated:
        user_profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            reviews.create(
                user=user_profile,
                book=book,
                rating=request.POST.get('rating'),
                body=request.POST.get('body')
            )

            reviews = Review.objects.all().filter(book=book)
            rating = reviews.aggregate(Avg('rating'))['rating__avg']
            book.rating = rating
            book.review_count = review_count + 1
            book.save()
            messages.success(request, 'Review successfully added')
            return redirect(reverse('book_detail', args=[book.id]))
        else:
            messages.error(
                request, 'Failed to add review.\
                    Please ensure the form is valid.')

    else:
        form = ReviewForm()
        if request.user.is_authenticated:
            reviewed = Review.objects.all().filter(
                book=book).filter(user=user_profile.id)
        else:
            reviewed = False

    context = {
        'book': book,
        'form': form,
        'reviews': reviews,
        'review_count': review_count,
        'reviewed': reviewed,
    }
    return render(request, 'books/book_detail.html', context)


@login_required
def add_book(request):
    """ Add a book to the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)

        if form.is_valid():
            book = form.save()
            if book.sale_price and book.sale_price > 0:
                book.discount = book.price - book.sale_price
                if book.sale_price and book.sale_price > book.price:
                    messages.error(
                        request, 'Sale price must be lower\
                             than current price!')
                    return redirect(reverse('edit_book', args=[book.id]))

            else:
                book.sale_price = None

            book.save()
            messages.success(request, 'Successfully added book!')
            return redirect(reverse('book_detail', args=[book.id]))
        else:
            messages.error(
                request, 'Failed to add book.\
                     Please ensure the form is valid.')
    else:
        form = BookForm()

    template = 'books/add_book.html'
    context = {
        'form': form,
        'on_page': True,
    }
    return render(request, template, context)


@login_required
def add_category(request):
    """ Add a category to the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully added category!')
            return redirect(reverse('add_category'))
        else:
            messages.error(
                request, 'Failed to add book.\
                     Please ensure the form is valid.')
    else:
        form = CategoryForm()
    template = 'books/add_category.html'
    context = {
        'form': form,
        'on_page': True,
    }
    return render(request, template, context)


@login_required
def edit_book(request, book_id):
    """ Edit a product in the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    book = get_object_or_404(Book, pk=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            book = form.save()
            if book.sale_price and book.sale_price > 0:
                book.discount = book.price - book.sale_price
                if book.sale_price and book.sale_price > book.price:
                    messages.error(
                        request, 'Sale price must be lower\
                             than current price!')
                    return redirect(reverse('edit_book', args=[book.id]))
            else:
                book.discount = None

            book.save()
            messages.success(request, 'Successfully updated book!')
            return redirect(reverse('book_detail', args=[book.id]))
        else:
            messages.error(
                request,
                'Failed to update product. Please ensure the form is valid.')
    else:
        form = BookForm(instance=book)
        messages.info(request, f'You are editing {book.title}')

    template = 'books/edit_book.html'
    context = {
        'form': form,
        'book': book,
        'on_page': True,
    }

    return render(request, template, context)


@login_required
def edit_category(request, category_id):
    """ Edit a category on add category page """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    category = get_object_or_404(Category, pk=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated category!')
            return redirect(reverse('add_category'))
        else:
            messages.error(
                request,
                'Failed to update category. Please ensure the form is valid.')
    else:
        form = CategoryForm(instance=category)
        messages.info(request, f'You are editing {category.friendly_name}')

    template = 'books/edit_category.html'
    context = {
        'form': form,
        'category': category,
        'on_page': True,
    }

    return render(request, template, context)


@login_required
def delete_book(request, book_id):
    """ Delete a product in the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    book = get_object_or_404(Book, pk=book_id)
    book.delete()
    messages.success(request, 'Book deleted')

    return redirect(reverse('books'))


@login_required
def delete_category(request, category_id):
    """ Delete a category"""
    if not request.user.is_superuser:
        messages.error(request, 'Sorry only store owners can do that.')
        return redirect(reverse('home'))

    category = get_object_or_404(Category, pk=category_id)
    category.delete()
    messages.success(request, 'Category deleted')

    return redirect(reverse('add_category'))


@login_required
def edit_review(request, review_id):
    """ Edit review"""
    review = get_object_or_404(Review, pk=review_id)
    book = review.book

    if request.user.id != review.user.user.id:
        messages.error(request, 'Sorry, you do not have access to that.')
        return redirect(
            reverse('book_detail', args=[book.id]))

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            reviews = Review.objects.all().filter(book=book)
            rating = reviews.aggregate(Avg('rating'))['rating__avg']
            book.rating = rating
            book.save()
            messages.success(request, 'Successfully updated review!')
            return redirect(reverse('book_detail', args=[book.id]))
        else:
            messages.error(
                request,
                "Failed to update review - please check form and try again")
    else:
        form = ReviewForm(instance=review)

    messages.info(request, f"You are editing your review of {book}.")
    template = 'books/book_detail.html'
    context = {
        'form': form,
        'review': review,
        'book': book,
        'edit': True
    }

    return render(request, template, context)


@login_required
def delete_review(request, review_id):
    """ Delete review """
    review = get_object_or_404(Review, pk=review_id)
    book = review.book

    if request.user.id != review.user.user.id:
        messages.error(request, 'Sorry, you do not have access to that.')
        return redirect(
            reverse('book_detail', args=[book.id]))

    review.delete()
    reviews = Review.objects.all().filter(book=book)
    rating = reviews.aggregate(Avg('rating'))['rating__avg']
    book.rating = rating
    book.review_count -= 1
    book.save()
    messages.success(request, 'Review successfully deleted!')
    return redirect(reverse('book_detail', args=[book.id]))
