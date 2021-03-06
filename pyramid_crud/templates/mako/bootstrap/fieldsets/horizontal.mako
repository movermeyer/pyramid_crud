<%page args="fieldset"/>
<fieldset class="form-horizontal">
	% if fieldset["title"]:
		<legend>${fieldset["title"]}</legend>
    % endif
    % for field in fieldset['fields']:
        % if getattr(field.widget, 'input_type', None) == 'hidden':
            ${field()}
        % else:
            <div class="form-group ${'has-error' if field.errors else ''}">
                ${field.label(class_='control-label col-sm-2')}
                <div class="col-sm-10">
                    ${field(class_='form-control')}
                    % if getattr(field, 'description', ''):
                        <span class="help-block">${field.description}</span>
                    % endif
                    % if field.errors:
                        <div class="alert alert-danger">
                            % for msg in field.errors:
                                ${msg}
                                % if not loop.last:
                                    <br />
                                % endif
                            % endfor
                        </div>
                    % endif
                 </div>
           </div>
        % endif
    % endfor
</fieldset>
