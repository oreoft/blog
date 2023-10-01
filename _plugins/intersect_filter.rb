module Jekyll
  module IntersectFilter
    def intersect(input, other_array)
      input & other_array
    end
  end
end

Liquid::Template.register_filter(Jekyll::IntersectFilter)
