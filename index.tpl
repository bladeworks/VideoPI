<!DOCTYPE html>
<html>
	<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<link href="http://code.jquery.com/mobile/latest/jquery.mobile.css" rel="stylesheet" type="text/css" />
	<link href="/static/css/videopi.css" rel="stylesheet" type="text/css" />
	<script src="http://code.jquery.com/jquery-1.9.1.min.js"></script>
	<script src="http://code.jquery.com/mobile/latest/jquery.mobile.js"></script>
	<meta charset=utf-8 />
	<title>Raspberry Controller</title>
	</head>
	<body>
	  <div id="main" data-role="page" data-theme="b" data-content-theme="b">
	  	<script type="text/javascript">
			$("#main").on('pageshow', function() {
				refreshHistory();
			});
	  	</script>
	  	<div data-role="popup" id="message"></div>
	  	<div data-role="header">
	  		<a href="/" data-icon="home" data-ajax="false">Home</a>
	  		<h1>Controller</h1>
	  	</div>
	  	<div data-role="content">
  			<div data-role="controlgroup" data-type="horizontal">
	  			<a href="#" onclick="control('pause');return false" data-role="button" data-icon="custom" id="pause" data-theme="a" data-iconpos="notext">Play/Pause</a>
	  			<a href="#" onclick="control('stop');return false" data-role="button" data-icon="custom" id="stop" data-theme="a" data-iconpos="notext">Stop</a>
	  			<a href="#" onclick="control('voldown');return false" data-role="button" data-icon="custom" id="voldown" data-theme="a" data-iconpos="notext">Voldown</a>
	  			<a href="#" onclick="control('volup');return false" data-role="button" data-icon="custom" id="volup" data-theme="a" data-iconpos="notext">Volup</a>
	  		</div>
	  		<div data-role="collapsible" data-collapsed="false" data-theme="b" data-content-theme="b">
	  			<h3>Now Playing</h3>
	  			%setdefault('currentVideo', None)
	  			%if currentVideo and currentVideo.availableFormat:
	  			<div data-role="controlgroup" data-type="horizontal">
		  			%for f in currentVideo.availableFormat:
		  			<a href="/forward?site={{currentVideo.site}}&url={{currentVideo.url}}&format={{f}}" data-role="button" class="
		  			%if currentVideo.currentFormat == f: 
		  			ui-disabled
		  			%end
		  			">{{currentVideo.formatDict[f]}}</a>
		  			%end
	  			</div>
	  			%end
	  			<div>
	  				%setdefault('title', 'N/A')
	  				%setdefault('duration', 'N/A')
	  				<p>Title: {{title}}</p>
	  				<p>Duration: {{duration}}</p>
	  			</div>
	  		</div>
	  		<div data-role="collapsible" data-collapsed="true" data-theme="b" data-content-theme="b">
	  			<h3>Browse</h3>
	  			<div data-role="controlgroup">
		  			%for site, data in iter(sorted(websites.iteritems())):
			  			<a href="/forward?url={{data['url']}}&site={{site}}" data-ajax="false" data-role="button" data-icon="custom" id="{{site}}" data-theme="c">{{data['title']}}</a>	
		  			%end
		  		</div>
	  		</div>
	  		<div data-role="collapsible" data-collapsed="true" data-theme="d" data-content-theme="d">
	  			<h3>History</h3>
	  			<div class="ui-bar">
	  				<a href="#" onclick="clearHistory();return false" data-role="button" data-inline="true" data-mini="true">Clear all the history</a>
	  			</div>
	  			<ul data-role="listview" data-inset="true" data-filter="true" data-filter-placeholder="Find history" id="historyListView">
	  			</ul>
	  		</div>
	  	</div>
	  	<div data-role="footer">
	  		<h4>Powered by blade&nbsp;&copy;&nbsp;<b>bladeworks</b></h4>
	  	</div>
	  </div>
	</body>
	<script src="/static/js/videopi.js"></script>
</html>