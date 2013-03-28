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
		%setdefault('currentVideo', None)
	  	<script>
	  		$('#main').on('pageshow', function() {
	  			getProgress();
	  		});
	  	</script>
	  	<div data-role="popup" id="message" class="ui-content" data-theme="e"></div>
	  	<div data-role="header" data-theme="a">
	  		<a href="/" data-icon="ihome" data-ajax="false" data-iconpos="notext" class="ui-icon-nodisc">Home</a>
	  		<h1>Remote Control</h1>
	  		<div data-role="controlgroup" data-type="horizontal" class="ui-btn-right">
		  		<a href="#confirmDialog" data-rel="popup" data-position-to="window" data-inline="true" data-transition="pop" data-icon="power" data-iconpos="notext" class="ui-icon-nodisc" data-role="button">Shutdown</a>
		  		%include confirm_dialog id="confirmDialog", title="Power off?", sub_title="Are you sure to power off the box?", message="You have to re-plug the power to start the box again", yes_url="/shutdown"
		  		<a href="#resetConfirmDialog" data-rel="popup" data-position-to="window" data-inline="true" data-transition="pop" data-icon="restart" data-iconpos="notext" class="ui-icon-nodisc" data-role="button">Restart</a>
		  		%include confirm_dialog id="resetConfirmDialog", title="Restart?", sub_title="Are you sure to restart the box?", message="You may lose some unsaved information.", yes_url="/restart"
		  	</div>
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
			%if currentVideo and int(currentVideo.duration) > 0:
				<input type="range" id="progressbar" value="0" min="0" max="{{currentVideo.duration}}" data-highlight="true" data-mini="true"
				%if (not currentVideo.sections) or len(currentVideo.sections) == 1:
					disabled="disabled"
				%end
				data-theme="b"/>
			%end
	  		<div data-role="collapsible" data-collapsed="false" data-theme="b" data-content-theme="b">
	  			<h3>Now Playing</h3>
	  			%if currentVideo and currentVideo.allRelatedVideo:
		  			<div data-role="controlgroup" data-type="horizontal" id="relatedVideo">
		  				%if currentVideo.previousVideo:
			  			<a href="/forward?site={{currentVideo.site}}&url={{currentVideo.previousVideo}}" data-role="button" data-ajax="false">上一集</a>
			  			%end
		  				%if currentVideo.nextVideo:
			  			<a href="/forward?site={{currentVideo.site}}&url={{currentVideo.nextVideo}}" data-role="button" data-ajax="false">下一集</a>
			  			%end
			  			%if currentVideo.allRelatedVideo:
						<a href="#allVideo" data-rel="popup" data-role="button" data-position-to="window" data-inline="true">全集</a>
						<div data-role="popup" id="allVideo" data-theme="d">
							<ul data-role="listview" data-inset="true" data-theme="d">
								<li data-role="divider" data-theme="e">请选择视频</li>
								%for v in currentVideo.allRelatedVideo:
									<li data-theme=
										%if v['current']:
											'e'
										%else:
											'd'
										%end
										>
										<a href="/forward?site={{currentVideo.site}}&url={{v['url']}}" data-ajax="false">{{v['title']}}</a>
									</li>
								%end
							</ul>
						</div>
			  			%end>
		  			</div>
	  			%end
	  			%if currentVideo and currentVideo.availableFormat:
		  			<div data-role="controlgroup" data-type="horizontal" id="formatSelect">
			  			%for f in currentVideo.availableFormat:
			  			<a href="/forward?site={{currentVideo.site}}&url={{currentVideo.url}}&format={{f}}" data-role="button" class="
			  			%if currentVideo.currentFormat == f: 
			  			ui-disabled
			  			%end
			  			" data-ajax="false">{{currentVideo.formatDict[f]}}</a>
			  			%end
		  			</div>
	  			%end
	  			<div class='well'>
	  				%if currentVideo:
		  				<p>Title: <span id="title">{{currentVideo.title}}</span></p>
		  				<p>Duration: <span id="duration">{{currentVideo.durationToStr()}}</span></p>
	  				%else:
		  				<p>Title: <span id="title">N/A</span></p>
		  				<p>Duration: <span id="duration">N/A</span></p>
	  				%end
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
	  			<ul data-role="listview" data-inset="true" data-filter="true" data-filter-placeholder="Find history" id="historyListView" data-split-icon="delete">
	  				%for h in history:
	                    <li>
	                        <a href="/play?id={{h.dbid}}" class="ui-link-inherit" data-ajax="false">
	                            <h3>{{h.title}}({{websites[h.site]['title']}})</h3>
	                            <p>总共{{h.durationToStr()}}(上次播放到{{h.formatDuration(h.progress)}})</p>
	                        </a>
	                        <a href="#" onclick="deleteHistory('{{h.dbid}}');return false"></a>
	                    </li>
                    %end
	  			</ul>
	  		</div>
	  	</div>
	  	<div data-role="footer" data-theme="a">
	  		<h4>Powered by blade&nbsp;&copy;&nbsp;<b>bladeworks</b></h4>
	  	</div>
	  </div>
	</body>
	<script src="/static/js/videopi.js"></script>
</html>