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
		<title>Raspberry Remote Control</title>
	</head>
	<body>
	  <div id="main" data-role="page" data-theme="b" data-content-theme="b">
	  	<script type="text/javascript">
			$("#main").on('pageshow', function() {
				refreshHistory();
			});
	  	</script>
	  	<div data-role="popup" id="message" class="ui-content" data-theme="e"></div>
	  	<div data-role="header">
	  		<a href="/" data-icon="home" data-ajax="false" data-iconpos="notext">Home</a>
	  		<h1>Remote Control</h1>
	  	</div>
	  	<div data-role="content">
  			<div data-role="navbar">
  				%for group in actionDesc:
  					<ul>
  						%for action in group:
  							<li>
  								<a href="#" onclick="control('{{action[0]}}');return false" data-theme="c" data-role="button" class="ctlbtn">
  									<img src="/static/img/{{action[0]}}.png" height="26" alt="{{action[1]}}"/>
  								</a>
  							</li>
  						%end for
  					</ul>
  				%end for
	  		</div>
	  		<div data-role="collapsible" data-collapsed="false" data-theme="b" data-content-theme="b">
	  			<h3>Now Playing</h3>
	  			%setdefault('currentVideo', None)
	  			%if currentVideo and currentVideo.availableFormat:
	  			<div data-role="controlgroup" data-type="horizontal" id="formatSelect">
		  			%for f in currentVideo.availableFormat:
		  			<a href="/forward?site={{currentVideo.site}}&url={{currentVideo.url}}&format={{f}}" data-role="button" class="
		  			%if currentVideo.currentFormat == f: 
		  			ui-disabled
		  			%end
		  			">{{currentVideo.formatDict[f]}}</a>
		  			%end
	  			</div>
	  			%end
	  			<div class='well'>
	  				%setdefault('title', 'N/A')
	  				%setdefault('duration', 'N/A')
	  				<p>Title: <span id="title">{{title}}</span></p>
	  				<p>Duration: <span id="duration">{{duration}}</span></p>
	  			</div>
	  		</div>
	  		<div data-role="collapsible" data-collapsed="true" data-theme="b" data-content-theme="c">
	  			<h3>Browse</h3>
	  			<ul data-role="listview" data-inset="true" data-theme="c" data-split-icon="info" data-split-theme="e">
		  			%for site, data in iter(sorted(websites.iteritems())):
		  			<li>
			  			<a href="/forward?url={{data['url']}}&site={{site}}" data-ajax="false" data-theme="c" data-icon="custom" id="{{site}}"><img src="{{data['icon']}}" class="ui-li-icon"/>
			  				{{data['title']}}
			  			</a>	
			  			<a href="#{{site}}info" data-rel="popup" data-position-to="window" data-transition="pop">Details</a>
			  		</li>
			  		<div data-role="popup" id="{{site}}info" class="ui-content" data-theme="e">
			  			<p>{{data['info']}}</p>
					</div>	
		  			%end
		  		</ul>
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