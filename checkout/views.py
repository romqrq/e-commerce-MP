from django.shortcuts import render, get_object_or_404, reverse, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import MakePaymentForm, OrderForm
from .models import OrderLineItem
from django.conf import settings
from django.utils import timezone
from products.models import Product
import stripe

# Create your views here.
stripe.api_key = settings.STRIPE_SECRET

# requires user to be logged in
@login_required()
def checkout(request):
    if request.method == "POST":
        # Takes all USER info from the OrderForm POSTED
        order_form = OrderForm(request.POST)
        # Takes all PAYMENT info from the MakePaymentForm POSTED
        payment_form = MakePaymentForm(request.POST)

        if order_form.is_valid() and payment_form.is_valid():
            order = order_form.save(commit=False)
            order.date = timezone.now()
            order.save()

            # Getting the information of what is being purchased
            # from the cart in the current session
            cart = request.session.get('cart', {})
            # We initialize a total of 0
            total = 0
            # Go over the id and quantities in our cart items
            for id, quantity in cart.items():
                # and from that we get our product
                product = get_object_or_404(Product, pk=id)
                total += quantity * product.price
                # We use the model we created for items
                order_line_item = OrderLineItem(
                    order=order,
                    product=product,
                    quantity=quantity
                )
                # Now that we've created the object with the information
                # from the cart, we can save it
                order_line_item.save()
            # Now that we know what they want to buy,
            # we try to charge using stripe in-built API
            try:
                customer = stripe.Charge.create(
                    # Stripe uses everything in cents so 10 euros has to be
                    # *100 to become 1000 cents
                    amount=int(total * 100),
                    currency="EUR",
                    # For the description we get the user email so from stripe
                    # dashboard we can see who bought the product
                    description=request.user.email,
                    # The stripe_id is the item that was hidden from the user
                    # and we get it upon form submission
                    card=payment_form.cleaned_data['stripe_id']
                )
            except stripe.error.CardError:
                messages.error(request, "Your card was declined!")

            if customer.paid:
                messages.error(request, "You have successfully paid")
                request.session['cart'] = {}
                return redirect(reverse('products'))
            else:
                messages.error(request, "Unable to take payment")
        # If one of the filled forms isn's valid:
        else:
            print(payment_form.errors)
            messages.error(request,
                           "We were unable to take a payment with that card!")
    # If there's no POST
    else:
        payment_form = MakePaymentForm()
        order_form = OrderForm()
    # The dictionary makes all these things available when the user clicks on
    # the checkout
    return render(request, "checkout.html", {
        "order_form": order_form,
        "payment_form": payment_form,
        "publishable": settings.STRIPE_PUBLISHABLE})
