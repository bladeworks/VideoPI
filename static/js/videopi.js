function refreshHistory() {
	console.log("Refresh history");
	$.get('/history', function(data) {
		$('#historyListView').html(data);
		$('#historyListView').listview('refresh');
	});
}
function control(action) {
	var url = "/control/" + action;
	$.post(url, function(data) {
		if (data !== "") {
			if (data === "OK") {
				if (action === "stop") {
					$('#title').html('N/A');
					$('#duration').html('N/A');
					$('#formatSelect').html('');
				}
				showMessage("The command has been sent to the server");
			} else {
				showMessage(data);
			}
		}
	});
}
function deleteHistory(id) {
	var url = "/delete/" + id;
	$.post(url, function(data) {
		refreshHistory();
	});
}
function clearHistory() {
	var url = "/clear";
	$.post(url, function(data) {
		refreshHistory();
	});
}
function showMessage(message) {
	$("#message").html(message);
	$("#message").popup('open');
	setTimeout(function() {
		$("#message").popup('close');
		$(".ctlbtn").removeClass('ui-btn-active');
	}, 1500);
}
