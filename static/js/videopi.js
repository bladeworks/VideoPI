function refreshHistory() {
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
					$('#relatedVideo').html('');
				}
				showMessage("");
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
function showMessage(message, timeout) {
	timeout = typeof timeout !== 'undefined' ? timeout : 1500;
	if (message === "") {
		$(".ctlbtn").removeClass('ui-btn-active');
		return;
	}
	$("#message").html(message);
	$("#message").popup('open');
	setTimeout(function() {
		$("#message").popup('close');
		$(".ctlbtn").removeClass('ui-btn-active');
	}, timeout);
}
function updateProgress() {
	$.get('/progress', function(data) {
		if(data['title'] !== $('#title').html()) {
			console.log("Refresh page");
			window.location = "/";
		}
		$('#title').html(data['title']);
		$('#duration').html(data['duration']);
		$('#progressbar').val(data['progress']);
		$('#progressbar').slider('refresh');
	});
}
function getProgress() {
	updateProgress();
	$("#progressbar").on('slidestop', function(event) {
		var gotoValue = $("#progressbar").val();
		console.log(gotoValue);
		$.post('/goto/' + gotoValue, function(data) {
			if (data !== 'OK') {
				showMessage("Nothing to do", 1500);
			}
		});
	});
	setInterval(function() {
		updateProgress();
	}, 5000);
}
function goAndRedirect(go, redirect) {
	$.get(go, function(data) {
		window.location = redirect;
	});
}
