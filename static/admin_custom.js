document.addEventListener("DOMContentLoaded", function() {
    // پیدا کردن تمام کادرهایی که کلمه price تو اسمشونه
    let priceInputs = document.querySelectorAll('input[name*="price"]');
    
    priceInputs.forEach(function(input) {
        // ساخت یک نوشته سبز رنگ زیر کادر قیمت
        let helper = document.createElement('div');
        helper.style.color = '#4caf50';
        helper.style.fontWeight = 'bold';
        helper.style.marginTop = '5px';
        helper.style.fontSize = '14px';
        input.parentNode.appendChild(helper);

        // هر وقت عددی تایپ شد، کاما بذار و به تومان بنویس
        input.addEventListener('keyup', function() {
            let val = this.value.replace(/,/g, '');
            if(!isNaN(val) && val !== '') {
                helper.innerText = Number(val).toLocaleString('fa-IR') + ' تومان';
            } else {
                helper.innerText = '';
            }
        });
        
        // همون اول که صفحه لود میشه هم یکبار اجراش کن
        input.dispatchEvent(new Event('keyup'));
    });
});