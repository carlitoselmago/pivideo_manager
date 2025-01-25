$(document).ready(function () {
    // Handle scanning network with AJAX
    $("body").on("click",'.scan-btn',function () {
        var ip_range = $(this).data('iprange');  // Get the data attribute value
        var setupElement = $(this).closest(".setup");
        setupElement.addClass("updating");
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

      // Handle updating device ip
      $("body").on("click",'.info-btn',function () {
        var deviceElement = $(this).closest(".device");
        deviceElement.addClass("updating")
        var ip = deviceElement.attr("data-ip");  // Get the data attribute value
        
        $.ajax({
            url: '/api/device_info/'+ip,
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
        
        $.ajax({
            url: '/api/show_screen/'+ip,
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
            url: '/api/reboot/'+ip,
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
            url: '/api/playback/'+ip+'/'+action,
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
            url: '/api/playbackall/'+iprange.replace("/", '_')+'/'+action,
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
