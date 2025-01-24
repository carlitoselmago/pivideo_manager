$(document).ready(function () {
    // Handle scanning network with AJAX
    $('#scan-btn').click(function () {
        var ip_range = $(this).data('iprange');  // Get the data attribute value

        $.ajax({
            url: '/api/scan',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ip_range: ip_range }),
            success: function (response) {
                alert(response.message);
                location.reload();  // Reload to show new devices
            },
            error: function (xhr) {
                alert("Error scanning network: " + xhr.responseText);
            }
        });
    });

    $(document).on('blur', '.editable-name', function () {
        let row = $(this).closest('.device');
        let ip = row.data('ip');
        let newName = $(this).text().trim();
        let master = row.find('.editable-master').is(':checked');

        $.ajax({
            url: '/api/update_device',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ip: ip, name: newName, master: master }),
            success: function (response) {
                console.log(response.message);
            },
            error: function (xhr) {
                alert("Error updating device: " + xhr.responseText);
            }
        });
    });

    // Handle master checkbox changes
    $(document).on('change', '.editable-master', function () {
        let row = $(this).closest('.device');
        let ip = row.data('ip');
        let newName = row.find('.editable-name').text().trim();
        let master = $(this).is(':checked');

        $.ajax({
            url: '/api/update_device',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ip: ip, name: newName, master: master }),
            success: function (response) {
                console.log(response.message);
            },
            error: function (xhr) {
                alert("Error updating device: " + xhr.responseText);
            }
        });
    });
});
