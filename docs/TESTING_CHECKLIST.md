# 🧪 **Complete Testing Checklist**

## **User Journey Testing**

### **1. New User Flow**
- [ ] `/start` command works
- [ ] Welcome message displays correctly
- [ ] Subscription plans shown with pricing
- [ ] "Back to Main Menu" buttons work

### **2. Subscription Flow**
- [ ] Click subscription plan
- [ ] Payment methods display correctly
- [ ] TON payment QR code generates
- [ ] Payment verification works
- [ ] Subscription activates after payment

### **3. Ad Management Flow**
- [ ] `/my_ads` command works
- [ ] Ad slots display correctly
- [ ] "Set Content" button works
- [ ] "Set Destinations" button works ✅ (Just fixed)
- [ ] "Set Schedule" button works
- [ ] Ad activation/deactivation works

### **4. Payment Testing**
- [ ] TON price API working
- [ ] QR code generation
- [ ] Payment verification on blockchain
- [ ] Multiple payment methods (BTC, ETH, USDT)

### **5. Scheduler Testing**
- [ ] Ads post to real groups
- [ ] Hourly posting interval (60 minutes)
- [ ] Error handling for failed posts
- [ ] Logs show successful posting

## **Admin Testing**

### **6. Admin Commands**
- [ ] `/add_group` - Add new groups
- [ ] `/list_groups` - View all groups
- [ ] `/admin_stats` - View statistics
- [ ] `/verify_payment` - Manual payment verification
- [ ] `/revenue_stats` - Revenue tracking

### **7. Database Testing**
- [ ] User registration
- [ ] Subscription management
- [ ] Ad slot creation
- [ ] Destination management
- [ ] Payment tracking

## **Error Handling**

### **8. Edge Cases**
- [ ] Invalid payment amounts
- [ ] Network errors
- [ ] Database connection issues
- [ ] Telegram API errors
- [ ] User input validation

## **Performance Testing**

### **9. Load Testing**
- [ ] Multiple concurrent users
- [ ] Database query performance
- [ ] Memory usage monitoring
- [ ] Response time testing

## **Security Testing**

### **10. Security Checks**
- [ ] Payment verification integrity
- [ ] User data protection
- [ ] Admin access control
- [ ] Input sanitization 