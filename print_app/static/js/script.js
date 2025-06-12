document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.querySelector('.custom-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            let fileName = e.target.files[0] ? e.target.files[0].name : 'Pilih file...';
            let nextSibling = e.target.nextElementSibling;
            nextSibling.innerText = fileName;
        });
    }

    if (typeof $ !== 'undefined' && $.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }

    const deleteForms = document.querySelectorAll('form[data-form-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmation = confirm('Apakah Anda yakin ingin menghapus pekerjaan ini? Aksi ini tidak dapat dibatalkan.');
            if (!confirmation) {
                e.preventDefault();
            }
        });
    });

    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(button => {
        button.addEventListener('click', function() {
            const pdfUrl = this.dataset.url;
            const printFrame = document.createElement('iframe');
            printFrame.style.position = 'absolute';
            printFrame.style.width = '0';
            printFrame.style.height = '0';
            printFrame.style.border = '0';
            printFrame.src = pdfUrl;
            document.body.appendChild(printFrame);
            printFrame.onload = function() {
                try {
                    printFrame.contentWindow.focus();
                    printFrame.contentWindow.print();
                } catch (e) {
                    console.error("Gagal memanggil dialog print:", e);
                    alert("Gagal membuka dialog print. Pastikan pop-up tidak diblokir.");
                }
                setTimeout(() => {
                    document.body.removeChild(printFrame);
                }, 2000);
            };
        });
    });
});