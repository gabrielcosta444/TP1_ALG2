window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng) {
            const properties = feature.properties || {};
            const isRestaurant = properties.category === "restaurant";
            return L.circleMarker(latlng, {
                radius: isRestaurant ? 8 : 5,
                color: properties.color || "#80868b",
                fillColor: properties.color || "#80868b",
                fillOpacity: 0.9,
                weight: isRestaurant ? 3 : 1
            }).bindTooltip(properties.label || "");
        }
    }
});
