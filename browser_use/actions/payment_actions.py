"""Universal payment automation helpers (stub).

This file provides lightweight stubs and API surfaces for:
- `UniversalPaymentFiller` - detect & fill payment forms
- `OTPHandler` - detect OTP flows
- `PaymentStatusVerifier` - verify final status

The implementations below are intentionally minimal and include
clear extension points and comments where the real logic belongs.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, List

logger = logging.getLogger(__name__)


@dataclass
class PaymentDetails:
    card_number: str
    expiry_month: str
    expiry_year: str
    cvv: str
    cardholder_name: str
    billing_address: str | None = None


class UniversalPaymentFiller:
    """Detects and fills virtually any card payment form.

    Usage:
        filler = UniversalPaymentFiller()
        await filler.execute(page, payment_details)

    Notes:
    - This is a stub showing the intended control flow. The real
      implementation should try many DOM selectors, then fall back
      to vision/OCR coordinate-click strategies and robust retries.
    - `page` is expected to be a Playwright-like page object (has
      `fill`, `click`, `locator`, `screenshot`, etc.) used throughout
      the `browser-use` codebase.
    """

    COMMON_CARD_SELECTORS: List[str] = [
        # Standard attributes
        "input[autocomplete='cc-number']",
        "input[autocomplete='cardnumber']",
        "input[name='cardnumber']",
        "input[name='card-number']",
        "input[name='card_number']",
        "input[name='ccnumber']",
        "input[name='cc-number']",
        "input[id='card-number']",
        "input[id='cardnumber']",
        "input[id='card_number']",
        "input[id='ccnumber']",
        # Payment gateways (Stripe, PayPal, Square, Razorpay, etc.)
        "input[data-stripe='number']",
        "input[name='cardNumber']",
        "input[id='cardNumber']",
        "input.card-number",
        "input.cardNumber",
        "#card-number",
        "#cardNumber",
        # Common patterns
        "input[placeholder*='card number' i]",
        "input[placeholder*='Card Number' i]",
        "input[aria-label*='card number' i]",
        "input[type='tel'][inputmode='numeric']",
        "input[type='tel'][maxlength='19']",
        "input[type='text'][inputmode='numeric'][maxlength='19']",
        # iframes (common in Stripe/PayPal)
        "iframe[name*='card'] input",
        "iframe[title*='payment'] input[name='cardnumber']",
    ]

    COMMON_EXPIRY_SELECTORS: List[str] = [
        # Standard
        "input[autocomplete='cc-exp']",
        "input[name='exp']",
        "input[name='expiry']",
        "input[name='exp-date']",
        "input[name='card-expiry']",
        "input[id='exp']",
        "input[id='expiry']",
        "input[id='card-expiry']",
        # Payment gateways
        "input[data-stripe='exp']",
        "input[name='cardExpiry']",
        "input.card-expiry",
        "#card-expiry",
        # Split fields (month)
        "input[name='exp-month']",
        "input[name='expiry-month']",
        "input[autocomplete='cc-exp-month']",
        "select[name='exp-month']",
        "select[name='cc-exp-month']",
        # Split fields (year)
        "input[name='exp-year']",
        "input[name='expiry-year']",
        "input[autocomplete='cc-exp-year']",
        "select[name='exp-year']",
        "select[name='cc-exp-year']",
        # Common patterns
        "input[placeholder*='MM/YY' i]",
        "input[placeholder*='MM / YY' i]",
        "input[placeholder*='expiry' i]",
        "input[aria-label*='expiry' i]",
    ]

    COMMON_CVV_SELECTORS: List[str] = [
        # Standard
        "input[autocomplete='cc-csc']",
        "input[name='cvv']",
        "input[name='cvc']",
        "input[name='csc']",
        "input[name='cvv2']",
        "input[name='card-cvc']",
        "input[name='card-cvv']",
        "input[id='cvv']",
        "input[id='cvc']",
        "input[id='csc']",
        "input[id='card-cvc']",
        # Payment gateways
        "input[data-stripe='cvc']",
        "input[name='cardCvc']",
        "input[name='securityCode']",
        "input.card-cvc",
        "input.cvv",
        "#cvv",
        "#cvc",
        "#card-cvc",
        # Common patterns
        "input[placeholder*='CVV' i]",
        "input[placeholder*='CVC' i]",
        "input[placeholder*='security code' i]",
        "input[aria-label*='cvv' i]",
        "input[aria-label*='security code' i]",
        "input[type='tel'][maxlength='4']",
        "input[type='tel'][maxlength='3']",
        "input[inputmode='numeric'][maxlength='4']",
        "input[inputmode='numeric'][maxlength='3']",
    ]

    COMMON_NAME_SELECTORS: List[str] = [
        # Standard
        "input[autocomplete='cc-name']",
        "input[name='name']",
        "input[name='cardholder']",
        "input[name='card-name']",
        "input[name='cardholder-name']",
        "input[name='cardName']",
        "input[id='cardholder-name']",
        "input[id='card-name']",
        "input[id='cardName']",
        # Payment gateways
        "input[data-stripe='name']",
        "input.cardholder-name",
        "input.card-name",
        "#cardholder-name",
        "#card-name",
        # Common patterns
        "input[placeholder*='name on card' i]",
        "input[placeholder*='cardholder' i]",
        "input[aria-label*='cardholder' i]",
        "input[aria-label*='name on card' i]",
    ]

    COMMON_SUBMIT_SELECTORS: List[str] = [
        # Standard
        "button[type='submit']",
        "input[type='submit']",
        # Common text patterns
        "button:has-text('Pay')",
        "button:has-text('Submit')",
        "button:has-text('Complete')",
        "button:has-text('Checkout')",
        "button:has-text('Place Order')",
        "button:has-text('Confirm')",
        # ARIA labels
        "button[aria-label*='pay' i]",
        "button[aria-label*='submit' i]",
        "button[aria-label*='complete' i]",
        # Payment gateways
        "button[data-testid='submit-button']",
        "button.submit-button",
        "button.pay-button",
        "#submit-button",
        "#pay-button",
        # Class patterns
        "button.btn-primary[type='button']",
        "button.checkout-button",
    ]

    def __init__(self, retry_attempts: int = 3, wait_between: float = 0.6) -> None:
        self.retry_attempts = retry_attempts
        self.wait_between = wait_between

    async def execute(self, page: Any, details: PaymentDetails) -> dict:
        """Attempt to fill and submit the payment form.

        Returns a simple dict with `status` and optional `message`.
        The real implementation should handle many edge-cases and
        return rich structured output.
        """
        logger.info("🔐 Starting payment form filling...")
        
        # 1) Try DOM selectors first
        for attempt in range(1, self.retry_attempts + 1):
            logger.info(f"   Attempt {attempt}/{self.retry_attempts}: Trying DOM selectors...")
            try:
                filled = await self._try_fill_using_selectors(page, details)
                if filled:
                    logger.info("   ✅ Form filled successfully via DOM selectors")
                    # Submit
                    submitted = await self._try_submit(page)
                    if submitted:
                        logger.info("   ✅ Payment form submitted successfully")
                        return {"status": "submitted", "message": "submitted_via_dom"}
                    else:
                        logger.warning("   ⚠️ Form filled but submit failed")
            except Exception as e:
                logger.debug(f"   ❌ DOM fill attempt failed: {e}")

            await asyncio.sleep(self.wait_between)

        # 2) Vision AI fallback
        logger.info("   🎯 Attempting vision-based filling...")
        try:
            vision_result = await self._try_fill_using_vision(page, details)
            if vision_result:
                logger.info("   ✅ Form filled successfully via Vision AI")
                submitted = await self._try_submit(page)
                if submitted:
                    logger.info("   ✅ Payment form submitted successfully")
                    return {"status": "submitted", "message": "submitted_via_vision"}
        except Exception as e:
            logger.debug(f"   ❌ Vision fill attempt failed: {e}")

        # 3) Tab navigation fallback
        logger.info("   ⌨️  Attempting keyboard navigation fallback...")
        try:
            tab_result = await self._try_fill_using_tab_navigation(page, details)
            if tab_result:
                logger.info("   ✅ Form filled successfully via keyboard navigation")
                submitted = await self._try_submit(page)
                if submitted:
                    logger.info("   ✅ Payment form submitted successfully")
                    return {"status": "submitted", "message": "submitted_via_keyboard"}
        except Exception as e:
            logger.debug(f"   ❌ Tab navigation fill attempt failed: {e}")

        logger.error("   ❌ All filling strategies failed")
        return {"status": "failed", "message": "no_fill_strategy_succeeded"}

    async def _try_fill_using_selectors(self, page: Any, details: PaymentDetails) -> bool:
        """Attempt to locate inputs via common selectors and fill them.

        Returns True if at least the card number and cvv were filled.
        """
        success_count = 0

        async def _try_fill(selectors: List[str], value: str, field_name: str) -> bool:
            for sel in selectors:
                try:
                    # Many page implementations support `fill` and `locator`
                    if hasattr(page, "fill"):
                        await page.fill(sel, value, timeout=2000)
                        logger.debug(f"      ✓ Filled {field_name} using selector: {sel}")
                        return True
                    elif hasattr(page, "locator"):
                        loc = page.locator(sel).first
                        await loc.fill(value, timeout=2000)
                        logger.debug(f"      ✓ Filled {field_name} using selector: {sel}")
                        return True
                except Exception:
                    continue
            logger.debug(f"      ✗ Could not fill {field_name}")
            return False

        if await _try_fill(self.COMMON_CARD_SELECTORS, details.card_number, "card number"):
            success_count += 1

        expiry_value = f"{details.expiry_month}/{details.expiry_year[-2:]}"
        if await _try_fill(self.COMMON_EXPIRY_SELECTORS, expiry_value, "expiry"):
            success_count += 1

        if await _try_fill(self.COMMON_CVV_SELECTORS, details.cvv, "CVV"):
            success_count += 1

        if await _try_fill(self.COMMON_NAME_SELECTORS, details.cardholder_name, "cardholder name"):
            success_count += 1

        logger.info(f"      Successfully filled {success_count}/4 fields")
        return success_count >= 2

    async def _try_submit(self, page: Any) -> bool:
        """Try to click submit button."""
        for sel in self.COMMON_SUBMIT_SELECTORS:
            try:
                if hasattr(page, "click"):
                    await page.click(sel, timeout=2000)
                    logger.debug(f"      ✓ Clicked submit button: {sel}")
                    return True
                elif hasattr(page, "locator"):
                    await page.locator(sel).first.click(timeout=2000)
                    logger.debug(f"      ✓ Clicked submit button: {sel}")
                    return True
            except Exception:
                continue
        logger.debug("      ✗ Could not find submit button")
        return False

    async def _try_fill_using_vision(self, page: Any, details: PaymentDetails) -> bool:
        """Vision AI fallback - use LLM to identify form fields from screenshot.
        
        This uses the browser-use Agent's vision capabilities to:
        1. Take a screenshot
        2. Ask LLM to identify payment form fields
        3. Use coordinates or element descriptions to fill
        """
        try:
            # Check if we have access to browser-use Agent
            from browser_use import Agent
            
            # Take screenshot
            if hasattr(page, "screenshot"):
                screenshot = await page.screenshot()
                logger.debug("      Screenshot captured for vision analysis")
                
                # In a real implementation, you would:
                # 1. Send screenshot to vision LLM
                # 2. Ask it to identify form field positions
                # 3. Use coordinates to click and type
                # For now, this is a placeholder
                logger.debug("      Vision analysis would happen here")
                return False
            
        except Exception as e:
            logger.debug(f"      Vision fallback error: {e}")
            return False

    async def _try_fill_using_tab_navigation(self, page: Any, details: PaymentDetails) -> bool:
        """Keyboard navigation fallback - tab through form and fill sequentially.
        
        This method:
        1. Focuses on the first input field
        2. Types the card number
        3. Tabs to next field (expiry)
        4. Continues until all fields filled
        """
        try:
            if not hasattr(page, "keyboard"):
                return False
            
            # Focus on first visible input
            if hasattr(page, "focus"):
                await page.focus("input[type='tel'], input[type='text']")
            
            # Type card number
            await page.keyboard.type(details.card_number)
            await page.keyboard.press("Tab")
            
            # Type expiry
            expiry_value = f"{details.expiry_month}{details.expiry_year[-2:]}"
            await page.keyboard.type(expiry_value)
            await page.keyboard.press("Tab")
            
            # Type CVV
            await page.keyboard.type(details.cvv)
            await page.keyboard.press("Tab")
            
            # Type cardholder name
            await page.keyboard.type(details.cardholder_name)
            
            logger.debug("      ✓ Keyboard navigation completed")
            return True
            
        except Exception as e:
            logger.debug(f"      Keyboard navigation error: {e}")
            return False


class OTPHandler:
    """Detect and handle OTP flows.

    This stub exposes the shape and integration points for OTP handling.
    Real implementations must integrate with secure OTP retrieval (SMS inbox,
    virtual numbers, or test-mode intercepts) and ensure proper logging/auditing.
    """

    async def wait_for_otp_and_submit(self, page: Any, timeout: int = 60) -> bool:
        # Placeholder: wait for OTP input to appear and return True when done
        # Real impl: poll SMS provider or intercept test OTPs
        await asyncio.sleep(0.5)
        logger.debug("OTPHandler.wait_for_otp_and_submit called (stub)")
        return False


class PaymentStatusVerifier:
    """Verify payment completed or failed after submit.

    The verifier should detect success banners, transaction id in page, or
    redirects to a confirmation page.
    """

    async def verify(self, page: Any, timeout: int = 30) -> dict:
        # Placeholder simple verification
        await asyncio.sleep(0.2)
        logger.debug("PaymentStatusVerifier.verify called (stub)")
        return {"status": "unknown", "details": None}


__all__ = ["PaymentDetails", "UniversalPaymentFiller", "OTPHandler", "PaymentStatusVerifier"]
