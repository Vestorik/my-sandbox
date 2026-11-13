# tuple
t1 = {1, "three", :four, false}
t1 |> elem(0)
new_tuple  = t1 |> put_elem(1, "snake")

# Keyword list
list = [ title: "fsfs", emered: 2011]
list |> Keyword.get(:title)

# maps
data = %{"title" => 121, :pw => "functional"}
data[:title] # nil or 121
data.pw # nil or functional
%{pw: "functional"} # nil or 121

# strings
# binary str - only "" dable quote
"test"
"rsult #{1+2}" # calculate in str


#  io
new_tuple |> IO.inspect
