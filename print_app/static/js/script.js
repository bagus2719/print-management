// Menunggu seluruh konten halaman dimuat
document.addEventListener('DOMContentLoaded', function() {

    // 1. Script untuk menampilkan nama file pada input file custom
    const fileInput = document.querySelector('.custom-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            let fileName = e.target.files[0] ? e.target.files[0].name : 'Pilih file...';
            let nextSibling = e.target.nextElementSibling;
            nextSibling.innerText = fileName;
        });
    }

    // 2. Mengaktifkan Bootstrap Tooltips
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    if (tooltips.length > 0 && typeof $ !== 'undefined' && $.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }

    // 3. Script untuk konfirmasi penghapusan
    const deleteForms = document.querySelectorAll('form[data-form-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmation = confirm('Apakah Anda yakin ingin menghapus pekerjaan ini? Aksi ini tidak dapat dibatalkan.');
            if (!confirmation) {
                e.preventDefault();
            }
        });
    });

});