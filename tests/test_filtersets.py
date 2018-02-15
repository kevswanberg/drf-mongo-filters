from collections import OrderedDict
from unittest import TestCase
from unittest import mock
from django.http import QueryDict
from rest_framework.exceptions import ValidationError
from mongoengine import Document, fields


from drf_mongo_filters import filters
from drf_mongo_filters import Filterset, ModelFilterset

from .models import SimpleDoc, DeepDoc

class BaseTests(TestCase):
    def test_declaration(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter()
            baz = filters.BooleanFilter(name='babaz')
        fs = TestFS({})

        self.assertEqual(list(fs.filters.keys()), ['foo', 'bar', 'baz'])
        self.assertIsInstance(fs.filters['foo'], filters.CharFilter)
        self.assertIsInstance(fs.filters['bar'], filters.IntegerFilter)
        self.assertIsInstance(fs.filters['baz'], filters.BooleanFilter)

        self.assertEqual([ f.field.source for f in fs.filters.values() ], ['foo', 'bar', 'babaz'])


    def test_inheritance(self):
        class BaseFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.CharFilter()
        class TestFS(BaseFS):
            bar = filters.IntegerFilter(name='babar')
            baz = filters.CharFilter()
        fs = TestFS({})

        self.assertEqual(list(fs.filters.keys()), ['foo', 'bar', 'baz'])
        self.assertIsInstance(fs.filters['foo'], filters.CharFilter)
        self.assertIsInstance(fs.filters['bar'], filters.IntegerFilter)
        self.assertIsInstance(fs.filters['baz'], filters.CharFilter)

        self.assertEqual([ f.field.source for f in fs.filters.values() ], ['foo', 'babar', 'baz'])


    def test_parsing_query(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter(name="babar")
            baz = filters.BooleanFilter()

        fs = TestFS(QueryDict("foo=Foo&babar=123&baz=true"))
        self.assertEqual(fs.values, OrderedDict([ ('foo','Foo'), ('bar', 123), ('baz', True) ]))

    def test_parsing_data(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter(name="babar")
            baz = filters.BooleanFilter()

        fs = TestFS({ 'foo': "Foo", 'babar': "123", 'baz': "true" })
        self.assertEqual(fs.values, OrderedDict([ ('foo','Foo'), ('bar', 123), ('baz', True) ]))

    def test_parsing_missed(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter()
            baz = filters.BooleanFilter()

        fs = TestFS({'foo':"Foo", 'baz': "true"})
        self.assertEqual(fs.values, OrderedDict([ ('foo','Foo'), ('baz', True) ]))

    def test_parsing_invalid(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter()
            baz = filters.BooleanFilter()

        fs = TestFS(QueryDict("foo=Foo&bar=xxx&baz=true"))
        with self.assertRaises(ValidationError):
            values = fs.values

    def test_filtering(self):
        class TestFS(Filterset):
            foo = filters.CharFilter()
            bar = filters.IntegerFilter(source='babar')
            baz = filters.CharFilter()

        qs = mock.Mock()
        qs.filter = mock.Mock(return_value=qs)
        fs = TestFS({ 'foo': "Foo", 'bar': 123 })

        fs.filter_queryset(qs)

        qs.filter.assert_has_calls([
            mock.call(foo="Foo"),
            mock.call(babar=123)
        ])

    def test_method_filtering(self):
        class TestFS(Filterset):
            foo = filters.CharFilter(method='filter_foo')

            def filter_foo(self, queryset, field_name, field_value):
                return queryset.filter(**{field_name: field_value})

        qs = mock.Mock()
        qs.filter = mock.Mock(return_value=qs)
        fs = TestFS({ 'foo': "Foo", 'bar': 123 })

        fs.filter_queryset(qs)

        qs.filter.assert_has_calls([
            mock.call(foo="Foo"),
        ])
        

class ModelTests(TestCase):
    def test_auto_types(self):

        class TestFS(ModelFilterset):
            class Meta:
                model = SimpleDoc

        fs = TestFS()
        self.assertIsInstance(fs.filters['f_str'], filters.CharFilter)
        self.assertIsInstance(fs.filters['f_url'], filters.CharFilter)
        self.assertIsInstance(fs.filters['f_eml'], filters.CharFilter)
        self.assertIsInstance(fs.filters['f_int'], filters.IntegerFilter)
        self.assertIsInstance(fs.filters['f_lng'], filters.IntegerFilter)
        self.assertIsInstance(fs.filters['f_flt'], filters.FloatFilter)
        self.assertIsInstance(fs.filters['f_dec'], filters.FloatFilter)
        self.assertIsInstance(fs.filters['f_bool'], filters.BooleanFilter)
        self.assertIsInstance(fs.filters['f_dt'], filters.DateTimeFilter)
        self.assertIsInstance(fs.filters['f_oid'], filters.ObjectIdFilter)
        self.assertIsInstance(fs.filters['f_ref'], filters.ReferenceFilter)
        self.assertIsInstance(fs.filters['f_uuid'], filters.UUIDFilter)

    def test_auto_derivatives(self):
        class FooField(fields.StringField):
            pass

        class MockModel(Document):
            foo = FooField()

        class TestFS(ModelFilterset):
            class Meta:
                model = MockModel

        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo']))
        self.assertIsInstance(fs.filters['foo'], filters.CharFilter)

    def test_auto_list(self):
        class TestFS(ModelFilterset):
            class Meta:
                model = DeepDoc
                fields = ['f_list']
        fs = TestFS()
        self.assertIsInstance(fs.filters['f_list'], filters.IntegerFilter)

    def test_custom_type(self):
        class FooField(fields.BaseField):
            pass

        class MockModel(Document):
            foo = FooField()

        class TestFS(ModelFilterset):
            filters_mapping = {
                FooField: filters.CharFilter
            }
            class Meta:
                model = MockModel
        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo']))

    def test_selecting(self):
        class MockModel(Document):
            foo = fields.StringField()
            bar = fields.StringField()
            baz = fields.StringField()

        class TestFS(ModelFilterset):
            class Meta:
                model = MockModel
                fields = ('foo','baz')

        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo', 'baz']))

    def test_excluding(self):
        class MockModel(Document):
            foo = fields.StringField()
            bar = fields.StringField()
            baz = fields.StringField()

        class TestFS(ModelFilterset):
            class Meta:
                model = MockModel
                exclude = ('bar',)

        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo', 'baz']))
        self.assertIsInstance(fs.filters['foo'], filters.CharFilter)

    def test_excluding_declared(self):
        class MockModel(Document):
            foo = fields.StringField()
            bar = fields.StringField()
            baz = fields.StringField()

        class BaseFS(ModelFilterset):
            class Meta:
                model = MockModel
            foo = filters.CharFilter()
            bar = filters.CharFilter()

        class TestFS(BaseFS):
            class Meta:
                model = MockModel
                exclude = ('bar', 'baz')
            baz = filters.CharFilter()
            quz = filters.CharFilter()

        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo', 'quz']))

    def test_redeclaring(self):
        class MockModel(Document):
            foo = fields.StringField()
            bar = fields.StringField()
            baz = fields.StringField()

        class TestFS(ModelFilterset):
            class Meta:
                model = MockModel
            bar = filters.IntegerFilter()
        fs = TestFS()
        self.assertEqual(set(fs.filters.keys()), set(['id', 'foo', 'bar', 'baz']))
        self.assertIsInstance(fs.filters['foo'], filters.CharFilter)
        self.assertIsInstance(fs.filters['bar'], filters.IntegerFilter)
        self.assertIsInstance(fs.filters['baz'], filters.CharFilter)

    def test_kwargs(self):
        class MockModel(Document):
            foo = fields.StringField()
            bar = fields.StringField()
            baz = fields.StringField()

        class TestFS(ModelFilterset):
            class Meta:
                model = MockModel
                kwargs = {
                    'foo': { 'lookup': 'gte' }
                }
        fs = TestFS()
        self.assertEqual(fs.filters['foo'].lookup_type, 'gte')
