from pyramid_crud import forms
from webob.multidict import MultiDict
from wtforms.fields import StringField, IntegerField
from sqlalchemy import Column, String, Integer, ForeignKey, inspect
from sqlalchemy.orm import relationship
from mock import MagicMock
from itertools import product
import pytest


@pytest.fixture
def formdata():
    return MultiDict()


@pytest.fixture
def form():
    return forms.ModelForm


@pytest.fixture
def subform():

    class SubForm(forms.ModelForm):
        test = StringField()

    return SubForm


@pytest.fixture
def generic_obj(Base):

    class GenericModel(Base):
        id = Column(Integer, primary_key=True)
        test_text = Column(String)
        test_int = Column(Integer)
    return GenericModel


def get_obj_test_matrix():
    "Create a matrix to test different types of objects."
    test_matrix = []
    for type_ in ['No values', 'Parent only', 'Children only', 'Both']:
        for children_no in range(3):
            for values_on_children_no in range(children_no + 1):
                test_matrix.append((type_, children_no,
                                    values_on_children_no))
    return test_matrix


# tests for all forms that inherit from the ModelForm
class TestNormalModelForm(object):

    @pytest.fixture(autouse=True)
    def _prepare(self, normal_form, inline_form):
        self.base_form = normal_form
        self.inline_form = inline_form

    def test_init_attrs(self, formdata):
        obj = object()
        f = forms.ModelForm(formdata, obj)
        assert f.formdata is formdata
        assert f.obj is obj

    def test__relationship_key(self, Model2_many_to_one, Model_one_pk,
                               form_factory):
        form = form_factory(base=self.base_form, model=Model_one_pk)
        OtherForm = form_factory(base=self.inline_form,
                                 model=Model2_many_to_one)
        assert form()._relationship_key(OtherForm) == 'models'

    def test__relationship_key_ambigous(self, Model_one_pk,
                                        Model2_many_to_one_multiple,
                                        form_factory):
        form = form_factory(base=self.base_form, model=Model_one_pk)
        OtherForm = form_factory(base=self.inline_form,
                                 model=Model2_many_to_one_multiple)
        with pytest.raises(ValueError):
            form()._relationship_key(OtherForm)

    def test__relationship_key_none(self, Model_one_pk, Model2_basic,
                                    form_factory):
        form = form_factory(base=self.base_form, model=Model_one_pk)
        OtherForm = form_factory(base=self.inline_form, model=Model2_basic)

        with pytest.raises(ValueError):
            form()._relationship_key(OtherForm)

    def test__relationship_key_explicitly(self, Model_one_pk,
                                          Model2_basic, form_factory):

        form = form_factory(base=self.base_form, model=Model_one_pk)
        other_form_fields = {'relationship_name': 'some_name'}
        OtherForm = form_factory(base=self.inline_form, model=Model2_basic,
                                 fields=other_form_fields)
        assert form()._relationship_key(OtherForm) == 'some_name'

    def test_process(self, formdata, generic_obj):
        # TODO: Test that parent "process" is called, too.
        form = self.base_form()
        form.process_inline = MagicMock()
        form.process(formdata, generic_obj, test='Test23')
        form.process_inline.assert_called_once_with(formdata, generic_obj,
                                                    test='Test23')

    def test_populate_obj(self, generic_obj):
        form = self.base_form()
        form.populate_obj_inline = MagicMock()
        form.populate_obj(generic_obj)
        form.populate_obj_inline.assert_called_once_with(generic_obj)


@pytest.fixture(params=[0, 1, 2])
def form_with_inlines(request, form_factory, model_factory,
                      normal_form):
    inline_form = forms.BaseInLine
    "Prepare a form with inlines"
    # request.param denotes number of different inline forms
    def get_default_cols():
        cols = [
            Column('test_text', String),
            Column('test_int', Integer),
        ]
        return cols
    ParentModel = model_factory(get_default_cols(), 'Parent')
    child1_cols = get_default_cols() + \
        [Column('parent_id', ForeignKey('parent.id'))]
    child1_rel = relationship(ParentModel, backref='child1')
    ChildModel1 = model_factory(child1_cols, 'Child1',
                                relationships={'parent': child1_rel})
    child2_cols = get_default_cols() + \
        [Column('parent_id', ForeignKey('parent.id'))]
    child2_rel = relationship(ParentModel, backref='child2')
    ChildModel2 = model_factory(child2_cols, 'Child2',
                                relationships={'parent': child2_rel})
    ChildModel1Form = form_factory(base=inline_form,
                                   name='ChildModel1Form',
                                   model=ChildModel1)
    ChildModel2Form = form_factory(base=inline_form,
                                   name='ChildModel2Form',
                                   model=ChildModel2)
    if request.param == 0:
        inlines = []
    elif request.param == 1:
        inlines = [ChildModel1Form]
    elif request.param == 2:
        inlines = [ChildModel1Form, ChildModel2Form]
    else:
        raise ValueError("Testing count %d not implemented"
                         % request.param)
    ParentModelForm = form_factory(fields={'inlines': inlines},
                                   base=normal_form,
                                   name='ParentModelForm',
                                   model=ParentModel)
    return ParentModelForm


@pytest.fixture(params=[0, 1, 2])
def formdata_with_inlines(request, form_with_inlines):
    Form = form_with_inlines
    "Prepare formdata to be processed"
    # request.param denotes number of inline forms with data
    formdata = MultiDict(test_int=1, test_text='parent')
    form_count = request.param
    for inline_index in range(1, len(Form.inlines) + 1):
        formdata['child%d_count' % inline_index] = form_count
        for item_index in range(request.param):
            int_key = 'child%d_%d_test_int' % (inline_index, item_index)
            text_key = 'child%d_%d_test_text' % (inline_index, item_index)
            int_val = int('%d%d' % (inline_index, item_index))
            text_val = 'text_child%d_%d' % (inline_index, item_index)
            formdata[int_key] = int_val
            formdata[text_key] = text_val
    return formdata, form_count


@pytest.fixture(params=get_obj_test_matrix())
def obj_with_inlines(request, form_with_inlines):
    # type_: How to initialize values, e.g. no values or only put values on
    # the parent.
    #
    # children_no: How many children the parent should have.
    #
    # values_on_children_no: How many children should get values if type_
    # determines there should be any
    type_, children_no, values_on_children_no = request.param

    Form = form_with_inlines
    inline_count = len(Form.inlines)

    # create parent
    obj = Form.Meta.model()

    # create desired number of children on each inline form
    for child_no, (index, inline) in \
            product(range(children_no), enumerate(Form.inlines, 1)):
        inline_model = inline.Meta.model
        child_obj = inline_model()
        assert inspect(inline_model).mapped_table.name == 'child%d' % index
        getattr(obj, 'child%d' % index).append(child_obj)

    # pass in values depending on type_
    if type_ == 'Parent only' or type_ == 'Both':
        obj.test_text = 'ParentModel'
        obj.test_int = 2
    if type_ == 'Children only' or type_ == 'Both':
        for inline_index in range(1, inline_count + 1):
            children = getattr(obj, 'child%d' % inline_index)
            for index, child in enumerate(children):
                text_val = 'text_child%d_model_%d' % (inline_index, index)
                int_val = int('1%d%d' % (inline_index, index))
                child.test_text = text_val
                child.test_int = int_val
    return (type_, children_no, values_on_children_no), obj


class TestNormalModelFormWithInline(object):

    def _parse_fixtures(self, form_with_inlines=None,
                        formdata_with_inlines=None,
                        obj_with_inlines=None):
        if form_with_inlines:
            self.Form = form_with_inlines
            self.inline_count = len(self.Form.inlines)
            self.ParentModel = self.Form.Meta.model

        if formdata_with_inlines:
            self.formdata, self.form_count = formdata_with_inlines

        if obj_with_inlines:
            obj_cfg, obj = obj_with_inlines
            self.value_type = obj_cfg[0]
            self.children_no = obj_cfg[1]
            self.values_on_children_no = obj_cfg[2]
            self.obj = obj

    # TODO: Test process_inline
    def test_process_inline(self, form_with_inlines, formdata_with_inlines):
        self._parse_fixtures(form_with_inlines, formdata_with_inlines)
        form = self.Form(self.formdata)
        form.process_inline(self.formdata)
        assert len(form.inlines) == self.inline_count
        for inline_index, inline in enumerate(form.inlines):
            inline_ref, forms = form.inline_fieldsets[inline.name]
            assert inline_ref is inline
            assert len(forms) == self.form_count
            for form_index, (inline_form, is_new) in enumerate(forms):
                assert is_new is True
                for field in inline_form:
                    assert field.data == self.formdata[field.name]

    def test_process_inline_none(self, form_with_inlines):
        self._parse_fixtures(form_with_inlines)
        form = self.Form()
        form.process_inline()
        assert len(form.inlines) == self.inline_count
        for inline_index, inline in enumerate(form.inlines):
            inline_ref, forms = form.inline_fieldsets[inline.name]
            assert inline_ref is inline
            assert len(forms) == 0

    def test_process_inline_with_obj(self, form_with_inlines,
                                     obj_with_inlines):
        self._parse_fixtures(form_with_inlines, None, obj_with_inlines)
        form = self.Form(obj=self.obj)
        if self.value_type == 'Parent only' or self.value_type == 'Both':
            assert form.test_text.data == 'ParentModel'
            assert form.test_int.data == 2

    def test_process_inline_obj_and_formdata(self):
        pass
    # TODO: Test process_inline deletion!
    # TODO: Test populate_obj_inline


# tests for all forms that inherit from _CoreModelForm (thus any form)
class TestAnyModelForm(object):

    @pytest.fixture(autouse=True)
    def _prepare(self, any_form, form_factory, model_factory):
        fields = {
            'test_text': StringField(),
            'test_int': IntegerField(),
        }
        self.form = form_factory(fields=fields, base=any_form)
        self.formdata = MultiDict(test_text='Test123', test_int=17)
        cols = [
            Column('id', Integer, primary_key=True),
            Column('test_text', String),
            Column('test_int', Integer),
        ]
        self.obj = model_factory(cols, name='GenericModel')

    def test_init(self):
        form = self.form(self.formdata)
        for key, value in self.formdata.items():
            assert getattr(form, key).data == value

    def test_init_obj_only(self):
        obj = self.obj(**self.formdata)
        form = self.form(obj=obj)
        for key, value in self.formdata.items():
            assert getattr(form, key).data == getattr(obj, key)

    def test_init_form_obj(self):
        obj = self.obj(test_text='ABC', test_int=3)
        form = self.form(self.formdata, obj)
        for key, value in self.formdata.items():
            assert getattr(form, key).data == value

    def test_init_form_one_val(self):
        obj = self.obj(**self.formdata)
        form = self.form(MultiDict(test_text='ABC'), obj)
        assert form.test_text.data == 'ABC'
        del self.formdata['test_text']
        for key, value in self.formdata.items():
            assert getattr(form, key).data == getattr(obj, key)

    def test_init_none(self):
        form = self.form()
        for key in self.formdata:
            assert getattr(form, key).data is None

    def test_title(self, form_factory, Model_one_pk, any_form):
        Form = form_factory(base=any_form, model=Model_one_pk)
        assert Form.title == 'Model'

    def test_title_plural(self, form_factory, Model_one_pk, any_form):
        Form = form_factory(base=any_form, model=Model_one_pk)
        assert Form.title_plural == 'Models'

    def test_name(self, form_factory, Model_one_pk, any_form):
        Form = form_factory(base=any_form, model=Model_one_pk)
        assert Form.name == 'model'

    def test_field_names(self, model_factory, form_factory, any_form):
        Model = model_factory([Column('val', Integer)])
        Form = form_factory(base=any_form, model=Model)
        field_names = ['val']
        assert Form.field_names == field_names

    def test_fieldsets(self, model_factory, form_factory, any_form):
        Model = model_factory([Column('val', Integer)])
        Form = form_factory(base=any_form, model=Model)
        fieldsets = [(None, {'fields': ['val']})]
        assert Form.fieldsets == fieldsets

    def test_fieldsets_empty(self, model_factory, form_factory, any_form):
        Model = model_factory()
        Form = form_factory(base=any_form, model=Model)
        fieldsets = [(None, {'fields': []})]
        assert Form.fieldsets == fieldsets

    def test_fieldsets_override(self, model_factory, form_factory, any_form):
        fieldsets = [('Test', {'fields': ['test', 'foo']})]
        Model = model_factory()
        Form = form_factory(base=any_form, model=Model,
                            fields={'fieldsets': fieldsets})
        assert Form.fieldsets == fieldsets

    def test_primary_keys(self, model_factory, form_factory, any_form,
                          DBSession):
        Model = model_factory()
        Form = form_factory(base=any_form, model=Model)
        obj = Model()
        DBSession.add(obj)
        DBSession.flush()
        assert Form(obj=obj).primary_keys == [('id', 1)]

    def test_primary_keys_multiple(self, model_factory, form_factory, any_form,
                                   DBSession):
        Model = model_factory([Column('id2', Integer, primary_key=True)])
        Form = form_factory(base=any_form, model=Model)
        obj = Model(id=1, id2=1)
        DBSession.add(obj)
        DBSession.flush()
        form_pks = sorted(Form(obj=obj).primary_keys, key=lambda t: t[0])
        assert form_pks == [('id', 1), ('id2', 1)]

    def test_primary_keys_no_obj(self, model_factory, form_factory, any_form):
        Model = model_factory()
        Form = form_factory(base=any_form, model=Model)
        with pytest.raises(AttributeError):
            Form().primary_keys

    def test_primary_keys_no_val(self, model_factory, form_factory, any_form):
        Model = model_factory()
        Form = form_factory(base=any_form, model=Model)
        assert Form(obj=Model()).primary_keys == [('id', None)]


# Tests for all forms that inherit from BaseInLine
class TestInlineModelForm(object):
    # TODO: test pks_from_formdata
    # TODO: test extra
    # TODO: test relationship_name
    pass
