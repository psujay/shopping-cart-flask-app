$(document).ready(function(){
	
	$("#register-form-link").click(function(){
		$("#register-form").show();
		$("#login-form").hide();
	});

	$("#login-form-link").click(function(){
		$("#login-form").show();
		$("#register-form").hide();
	});

});