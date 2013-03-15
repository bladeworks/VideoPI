<div data-role="popup" id="{{id}}" data-overlay-theme="a" data-theme="c" data-dismissible="false" class="ui-corner-all">
	<div data-role="header" data-theme="a" class="ui-corner-top">
		<h1>{{title}}</h1>
	</div>	
	<div data-role="content" data-theme="d" class="ui-corner-bottom ui-content">
		<h3 class="ui-title">{{sub_title}}</h3>
		<p>{{message}}</p>
		<a href="#" data-role="button" data-inline="true" data-rel="back" data-theme="c">No</a>
		<a href="{{yes_url}}" onclick="goAndRedirect('{{yes_url}}', '/'); return false;" data-role="button" data-inline="true" data-theme="e">Yes</a>
	</div>
</div>
