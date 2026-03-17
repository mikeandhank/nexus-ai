"""
Payment Integration Module
==========================
Stripe integration for balance reloads
"""
import os
import stripe
from typing import Dict, Tuple
from datetime import datetime


class PaymentManager:
    """
    Stripe payment integration for NexusOS
    """
    
    def __init__(self):
        self.stripe_api_key = os.environ.get('STRIPE_SECRET_KEY')
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        if self.stripe_api_key:
            stripe.api_key = self.stripe_api_key
    
    def create_payment_intent(self, amount: float, currency: str = "usd",
                              metadata: dict = None) -> Dict:
        """
        Create a Stripe payment intent for balance reload
        """
        if not self.stripe_api_key:
            return {"success": False, "error": "Stripe not configured"}
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True}
            )
            
            return {
                "success": True,
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    def create_checkout_session(self, amount: float, user_id: str,
                                success_url: str, cancel_url: str) -> Dict:
        """
        Create a Stripe Checkout session
        """
        if not self.stripe_api_key:
            return {"success": False, "error": "Stripe not configured"}
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'NexusOS Balance Reload',
                            'description': f'Add ${amount:.2f} to your account'
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={'user_id': user_id, 'amount': str(amount)}
            )
            
            return {
                "success": True,
                "checkout_url": session.url,
                "session_id": session.id
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    def verify_payment(self, payment_intent_id: str) -> Dict:
        """Verify payment was successful"""
        if not self.stripe_api_key:
            return {"success": False, "error": "Stripe not configured"}
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                return {
                    "success": True,
                    "amount": intent.amount / 100,
                    "currency": intent.currency,
                    "metadata": intent.metadata
                }
            return {"success": False, "status": intent.status}
                
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """Handle Stripe webhook events"""
        if not self.stripe_api_key or not self.webhook_secret:
            return {"success": False, "error": "Webhook not configured"}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            if event['type'] == 'payment_intent.succeeded':
                return {
                    "success": True,
                    "event_type": "payment_succeeded",
                    "data": event['data']['object']
                }
            
            return {"success": True, "event_type": event['type']}
                
        except stripe.error.SignatureVerificationError:
            return {"success": False, "error": "Invalid signature"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_refund(self, payment_intent_id: str, amount: float = None) -> Dict:
        """Create a refund"""
        if not self.stripe_api_key:
            return {"success": False, "error": "Stripe not configured"}
        
        try:
            refund_params = {"payment_intent": payment_intent_id}
            if amount:
                refund_params['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_params)
            
            return {
                "success": True,
                "refund_id": refund.id,
                "amount": refund.amount / 100,
                "status": refund.status
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}


# Singleton
_payment_manager = None

def get_payment_manager() -> PaymentManager:
    global _payment_manager
    if _payment_manager is None:
        _payment_manager = PaymentManager()
    return _payment_manager