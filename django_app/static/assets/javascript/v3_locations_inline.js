// ------------------------------------------------------------
// Django Admin hooks to improve the UI when adding and editing services.
// Not needed for the main app.
// ------------------------------------------------------------

(function () {
  "use strict";

  // ------------------------------------------------------------
  // Track all popup windows created via window.open()
  // and close them when the admin page unloads.
  // ------------------------------------------------------------
  function installPopupOpenHooks() {
    // Avoid wrapping more than once
    if (installPopupOpenHooks._installed) {
      return;
    }
    installPopupOpenHooks._installed = true;

    var originalOpen = window.open;
    var v3Popups = [];

    // Wrap window.open so we can record any popup that gets created
    window.open = function () {
      var win = originalOpen.apply(this, arguments);
      if (win && typeof win.closed === "boolean") {
        v3Popups.push(win);
      }
      return win;
    };

    // When this admin page is closed or navigated away, close all tracked popups
    window.addEventListener("beforeunload", function () {
      v3Popups.forEach(function (win) {
        try {
          if (win && !win.closed) {
            win.close();
          }
        } catch (e) {
          // Ignore any cross-window errors
        }
      });
    });
  }

  // ------------------------------------------------------------
  // Open the "add location" popup automatically after adding a location row
  // ------------------------------------------------------------
  function openAddPopupForLastLocationRow() {
    // Find all inline rows for V3_Service_Location
    var rows = document.querySelectorAll("tr.dynamic-v3_service_location_set");
    if (!rows.length) {
      return;
    }
    var lastRow = rows[rows.length - 1];

    // In that row, find the green "add-related" link for the Location FK
    var addLink = lastRow.querySelector(
      ".related-widget-wrapper-link.add-related"
    );
    if (addLink) {
      addLink.click();
    }
  }

  // ------------------------------------------------------------
  // Add listener for clicks on "Add a location"
  // ------------------------------------------------------------
  function installInlineAddAutoPopup() {
    // Listen for clicks on the "Add a location" inline add-row link
    document.body.addEventListener(
      "click",
      function (event) {
        var link = event.target.closest("tr.add-row a");
        if (!link) {
          return;
        }

        // Let Django handle the click and add the row first.
        // Then, once the DOM is updated, open the popup for the new row.
        window.setTimeout(openAddPopupForLastLocationRow, 100);
      },
      false
    );
  }

  // ------------------------------------------------------------
  // Create windowname_to_id() if it wasn't created by Django
  // ------------------------------------------------------------
  if (typeof window.windowname_to_id !== "function") {
    window.windowname_to_id = function (winName) {
      if (!winName) {
        return "";
      }
      // Strip leading "add_" or "change_"
      var name = winName.replace(/^(change|add)_/, "");

      // Reverse Django's id_to_windowname encoding (if used)
      // "__dot__" -> ".", "__dash__" -> "-"
      name = name.replace(/__dot__/g, ".").replace(/__dash__/g, "-");

      // What remains is the DOM element id
      return name;
    };
  }

  // ------------------------------------------------------------
  // Build URL for REST endpoint to get Location detail JSON
  // ------------------------------------------------------------
  function buildDetailUrl(locationId) {
    return "/admin/v3/location/" + encodeURIComponent(locationId) + "/json/";
  }

  // ------------------------------------------------------------
  // Update Location Detail display cells in the inline row
  // ------------------------------------------------------------
  function updateLocationDisplayCells(row, data) {
    function setCell(fieldSuffix, value) {
      var selector = "td.field-" + fieldSuffix + " p";
      var p = row.querySelector(selector);
      if (p) {
        p.textContent = value || "";
      }
    }

    setCell("address_1_display", data.address_1);
    setCell("address_2_display", data.address_2);
    setCell("town_display", data.town);
    setCell("postcode_display", data.postcode);
    setCell("opening_hours_display", data.opening_hours);
  }

  // ------------------------------------------------------------
  // Get JSON for the selected location and update the row
  // ------------------------------------------------------------
  function fetchAndUpdateLocation(row, locationId) {
    if (!locationId) {
      // Clear cells if nothing selected
      updateLocationDisplayCells(row, {
        address_1: "",
        address_2: "",
        town: "",
        postcode: "",
        opening_hours: "",
      });
      return;
    }

    var url = buildDetailUrl(locationId);
    fetch(url, { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error(
            "Failed to fetch location detail: " + response.status
          );
        }
        return response.json();
      })
      .then(function (data) {
        updateLocationDisplayCells(row, data);
      })
      .catch(function (err) {
        if (window.console && console.error) {
          console.error(err);
        }
      });
  }

  // ------------------------------------------------------------
  // When the Location popup closes, update the table row data
  // ------------------------------------------------------------
  function handleLocationPopupClose(win) {
    if (!win || !win.name) {
  	  return;
    }

    var fieldId = windowname_to_id(win.name);
    if (!fieldId) {
	  return;
    }

    // Try the raw ID first
    var elem = document.getElementById(fieldId);

    // If not found, strip any trailing "__<digits>" (or similar) and try again.
    // E.g. "id_v3_service_location_set-2-location__1"
    //   -> "id_v3_service_location_set-2-location"
    if (!elem) {
	  var strippedId = fieldId.replace(/(__\w+)+$/i, "");
	  if (strippedId !== fieldId) {
	    elem = document.getElementById(strippedId); 
	    fieldId = strippedId;
 	  }
    }

    if (!elem) {
	  return;
    }

    // Only handle the V3_Service_Location inline "location" FK:
    // id format: id_v3_service_location_set-<n>-location
    if (
	  elem.tagName.toLowerCase() !== "select" ||
	  !/^id_v3_service_location_set-\d+-location$/.test(fieldId)
    ) {
	  return;
    }

    var row = elem.closest("tr");
    if (!row) {
	  return;
    }

    var locationId = elem.value;
    toggleAddRelatedForRow(row, !!locationId);
    fetchAndUpdateLocation(row, locationId);
  }

  // ------------------------------------------------------------
  // 5Show/Hide the add location icon depending on if the row has a location assigned
  // ------------------------------------------------------------
  function toggleAddRelatedForRow(row, hasLocation) {
    var wrapper = row.querySelector(".related-widget-wrapper");
    if (!wrapper) return;
 
    var addLink = wrapper.querySelector(".related-widget-wrapper-link.add-related");
    if (!addLink) return;
 
    // Hide if we have a location; show otherwise
    addLink.style.display = hasLocation ? "none" : "";
  }

  // ------------------------------------------------------------
  // Intercept Django's popup dismiss functions so we can call our own functions
  // ------------------------------------------------------------
  function installPopupHooks() {
    // Make sure Django's functions exist first
    if (
      typeof window.dismissAddRelatedObjectPopup !== "function" ||
      typeof window.dismissChangeRelatedObjectPopup !== "function"
    ) {
      window.setTimeout(installPopupHooks, 150);
      return;
    }

    if (installPopupHooks._installed) {
      return;
    }
    installPopupHooks._installed = true;

    var originalDismissAdd = window.dismissAddRelatedObjectPopup;
    var originalDismissChange = window.dismissChangeRelatedObjectPopup;

    window.dismissAddRelatedObjectPopup = function (win, newId, newRepr) {
      // Let Django do its standard behaviour first
      originalDismissAdd.apply(this, arguments);
      // Then update our inline display cells
      handleLocationPopupClose(win);
    };

    window.dismissChangeRelatedObjectPopup = function (win, objId, newRepr) {
      // Let Django do its standard behaviour first
      originalDismissChange.apply(this, arguments);
      // Then update our inline display cells
      handleLocationPopupClose(win);
    };
  }

  // ------------------------------------------------------------
  // Install hooks when the page is loaded
  // ------------------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      installPopupHooks();
      installInlineAddAutoPopup();
      installPopupOpenHooks();
    });
  } else {
    installPopupHooks();
    installInlineAddAutoPopup();
    installPopupOpenHooks();
  }
})();
