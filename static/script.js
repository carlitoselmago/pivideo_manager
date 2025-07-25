$(document).ready(function () {

    let homeurl=$("body").attr("homeurl");

    // Handle scanning network with AJAX
    $("body").on("click",'.scan-btn',function () {
        var ip_range = $(this).attr('iprange');  // Get the data attribute value
        var setupElement = $(this).closest(".setup");
        setupElement.addClass("updating");
        
        $.ajax({
            url: homeurl+'/api/scan',
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

      // Handle updating device ip
      $("body").on("click",'.info-btn',function () {
        var deviceElement = $(this).closest(".device");
        deviceElement.addClass("updating")
        var ip = deviceElement.attr("data-ip");  // Get the data attribute value
        var mac = deviceElement.attr("data-mac");
        $.ajax({
            url: homeurl+'/api/device_info/'+ip+'/'+mac,
            type: 'GET',
            contentType: 'application/json',
            success: function (response) {
                
                //replace the line of the device
                deviceElement.replaceWith(response);
                
                //alert(response.message);
                //location.reload();  // Reload to show new devices
            },
            error: function (xhr) {
                alert("Error scanning network: " + xhr.responseText);
            }
        });
    });

     // Handle showing info on screen
     $("body").on("click",'.screen-btn',function () {
        var buttonelement = $(this);
        var deviceElement = $(this).closest(".device");
        buttonelement.addClass("updating")
        var ip = deviceElement.attr("data-ip");  // Get the data attribute value
        var mac = deviceElement.attr("data-mac");
        $.ajax({
            url: homeurl+'/api/show_screen/'+ip+'/'+mac,
            type: 'GET',
            contentType: 'application/json',
            success: function (response) {
              
            },
            error: function (xhr) {
                alert("Error scanning network: " + xhr.responseText);
            }
        });
        setTimeout(() => {
            console.log("finished showing msg")
            buttonelement.removeClass("updating");
          }, 20*1000);
    });

     // Handle reboot
     $("body").on("click",'.reboot-btn',function () {
        var deviceElement = $(this).closest(".device");
        deviceElement.addClass("updating")
        var ip = deviceElement.attr("data-ip");  // Get the data attribute value
        
        $.ajax({
            url: homeurl+'/api/reboot/'+ip,
            type: 'GET',
            contentType: 'application/json',
            success: function (response) {
                
                setTimeout(() => {
                    console.log("Finished booting.");
                    deviceElement.removeClass("updating");
                  }, 60*1000);
            },
            error: function (xhr) {
                alert("Error scanning network: " + xhr.responseText);
            }
        });
    });

    // Handle delete setup
     $("body").on("click",'.delete-btn',function () {
        if (!confirm("Are you sure you want to delete this setup? This action cannot be undone.")) {
            return;
        }
        var setupElement = $(this).closest(".setup");
        setupElement.addClass("updating");
        var iprange = setupElement.attr("iprange"); 
        
        $.ajax({
            url: homeurl+'/api/delete_setup',
            type: 'POST',
            contentType: 'application/json',
            data:JSON.stringify({ ip_range: iprange }),
            success: function (response) {
                    console.log("Finished deleting setup.");
                    location.reload();
            },
            error: function (xhr) {
                alert("Error deleting setup: " + xhr.responseText);
            }
        });
    });

    $("body").on("click",'.playback-btn',function () {
        var buttonelement = $(this);
        var deviceElement = $(this).closest(".device");
        buttonelement.addClass("updating")
        var ip = deviceElement.attr("data-ip"); 
        var action= buttonelement.attr("action");
        
        if (buttonelement.hasClass("togglerbtn")){
            $(".togglericon",buttonelement).toggle();
        }

        $.ajax({
            url: homeurl+'/api/playback/'+ip+'/'+action,
            type: 'GET',
            contentType: 'application/json',
            success: function (response) {
                buttonelement.removeClass("updating");
            },
            error: function (xhr) {
                alert("error on playbackcontrol: " + xhr.responseText);
            }
        });
    });

    $("body").on("click",'.playbackall-btn',function () {
        var buttonelement = $(this);
        var setupElement = $(this).closest(".setup");
        buttonelement.addClass("updating")
        var iprange = setupElement.attr("iprange"); 
        var action= buttonelement.attr("action");
        
        if (buttonelement.hasClass("togglerbtn")){
            $(".togglericon",buttonelement).toggle();
        }

        $.ajax({
            url: homeurl+'/api/playbackall/'+iprange.replace("/", '_')+'/'+action,
            type: 'GET',
            contentType: 'application/json',
            success: function (response) {
                setTimeout(() => {
                    buttonelement.removeClass("updating");
                }, 3*1000);
            },
            error: function (xhr) {
                alert("error on playbackcontrol: " + xhr.responseText);
            }
        });
    });

    $(document).on('blur', '.editable-name', function () {
        let row = $(this).closest('.device');
        let ip = row.data('ip');
        let newName = $(this).text().trim();
        let master = row.find('.editable-master').is(':checked');

        $.ajax({
            url: homeurl+'/api/update_device',
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
            url: homeurl+'/api/update_device',
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

    $('#openPopup').click(function() {
        $('#popupForm').fadeIn();
    });
    $('#closePopup').click(function() {
        $('#popupForm').fadeOut();
    });

    $('#setupForm').submit(function(event) {
        event.preventDefault();  // Prevent default form submission
       
        let formData = {
            name: $('#name').val(),
            iprange: $('#iprange').val(),
            password: $('#password').val()
        };

        $.ajax({
            url: homeurl+'/api/add_setup',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                alert(response.message);
                $('#popupForm').fadeOut();
                $('#setupForm')[0].reset();
                location.reload();  // Refresh to reflect the new setup
            },
            error: function(xhr) {
                alert('Error: ' + xhr.responseJSON.message);
            }
        });
    });


    document.querySelectorAll('.devices').forEach((deviceContainer) => {
        new Sortable(deviceContainer, {
            handle: '.dragarea',  // Allow dragging only by dragarea
            animation: 150,       // Smooth animation
            onEnd: function (evt) {
                let sortedDevices = [];
                
                // Iterate over the sorted items within this container only
                deviceContainer.querySelectorAll('.device').forEach((device, index) => {
                    sortedDevices.push({
                        mac: device.getAttribute('data-mac'),
                        order: index + 1,
                        container_id: deviceContainer.id  // Identify which sortable container
                    });
                });

                console.log(sortedDevices);  // Capture new order in console

                // Send sorted order to the server via AJAX
                $.ajax({
                    url: homeurl+'/api/update_device_order',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(sortedDevices),
                    success: function(response) {
                        console.log('Order updated successfully:', response);
                    },
                    error: function(xhr) {
                        console.error('Error updating order:', xhr.responseText);
                    }
                });
            }
        });
    });

});

