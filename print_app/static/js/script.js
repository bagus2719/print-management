document.addEventListener('DOMContentLoaded', function() {
    function formatRupiah(number) {
        return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(number);
    }

    // 1. Script untuk label input file
    const fileInput = document.querySelector('.custom-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const files = e.target.files;
            const label = e.target.nextElementSibling;
            if (files.length > 1) {
                label.innerText = `${files.length} file dipilih`;
            } else if (files.length === 1) {
                label.innerText = files[0].name;
            } else {
                label.innerText = 'Pilih file...';
            }
        });
    }

    // 2. Aktifkan Bootstrap Tooltips
    if (typeof $ !== 'undefined' && $.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }

    // 3. Konfirmasi hapus tunggal
    const deleteForms = document.querySelectorAll('form[data-form-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Apakah Anda yakin ingin menghapus pekerjaan ini?')) {
                e.preventDefault();
            }
        });
    });

    // 4. Tombol Print
    document.querySelectorAll('.btn-print').forEach(button => {
        button.addEventListener('click', function() {
            const pdfUrl = this.dataset.url;
            const printFrame = document.createElement('iframe');
            printFrame.style.display = 'none';
            printFrame.src = pdfUrl;
            document.body.appendChild(printFrame);
            printFrame.onload = () => {
                try {
                    printFrame.contentWindow.focus();
                    printFrame.contentWindow.print();
                } catch (e) {
                    alert("Gagal membuka dialog print. Pastikan pop-up tidak diblokir.");
                }
                setTimeout(() => document.body.removeChild(printFrame), 1000);
            };
        });
    });

    // 5. Kalkulasi biaya real-time di halaman configure
    const configPage = document.getElementById('config-page-data');
    if (configPage) {
        // ... (kode tidak berubah dari versi sebelumnya)
    }

    // --- LOGIKA BARU DI SINI ---

    // 6. Bulk delete & total terpilih di halaman ADMIN
    const adminDashboard = document.querySelector('#bulk-action-form');
    if (adminDashboard) {
        const selectAllAdmin = document.getElementById('select-all-admin');
        const checkboxesAdmin = document.querySelectorAll('.job-checkbox-admin');
        const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
        const adminSelectedRow = document.getElementById('admin-selected-total-row');
        const adminSelectedCostDisplay = document.getElementById('admin-selected-cost-display');

        const updateAdminActions = () => {
            const checkedCheckboxes = document.querySelectorAll('.job-checkbox-admin:checked');
            bulkDeleteBtn.disabled = checkedCheckboxes.length === 0;

            let selectedCost = 0;
            checkedCheckboxes.forEach(checkbox => {
                selectedCost += parseFloat(checkbox.closest('tr').dataset.cost);
            });

            if (checkedCheckboxes.length > 0) {
                adminSelectedCostDisplay.textContent = formatRupiah(selectedCost);
                adminSelectedRow.style.display = 'block';
            } else {
                adminSelectedRow.style.display = 'none';
            }
        };

        selectAllAdmin.addEventListener('change', () => {
            checkboxesAdmin.forEach(checkbox => checkbox.checked = selectAllAdmin.checked);
            updateAdminActions();
        });

        checkboxesAdmin.forEach(checkbox => checkbox.addEventListener('change', updateAdminActions));

        adminDashboard.addEventListener('submit', e => {
            if (!confirm('Apakah Anda yakin ingin menghapus semua pekerjaan yang dipilih? Aksi ini tidak dapat dibatalkan.')) {
                e.preventDefault();
            }
        });

        updateAdminActions(); // Panggil saat halaman dimuat
    }

    // 7. Kalkulasi total terpilih di halaman HISTORY PENGGUNA
    const historyTable = document.getElementById('history-table');
    if (historyTable) {
        const selectAllHistory = document.getElementById('select-all-history');
        const checkboxesHistory = document.querySelectorAll('.job-checkbox-history');
        const selectedTotalRow = document.getElementById('selected-total-row');
        const selectedCostDisplay = document.getElementById('selected-cost-display');

        const updateSelectedTotal = () => {
            let selectedCost = 0;
            const anyChecked = Array.from(checkboxesHistory).some(checkbox => {
                if (checkbox.checked) {
                    selectedCost += parseFloat(checkbox.closest('tr').dataset.cost);
                    return true;
                }
                return false;
            });

            if (anyChecked) {
                selectedCostDisplay.textContent = formatRupiah(selectedCost);
                selectedTotalRow.style.display = 'table-row';
            } else {
                selectedTotalRow.style.display = 'none';
            }
        };

        selectAllHistory.addEventListener('change', () => {
            checkboxesHistory.forEach(checkbox => checkbox.checked = selectAllHistory.checked);
            updateSelectedTotal();
        });

        checkboxesHistory.forEach(checkbox => checkbox.addEventListener('change', updateSelectedTotal));
    }
});